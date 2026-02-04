"""리포터 에이전트 - 분석 결과 종합 리포트 생성"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from jinja2 import Environment, FileSystemLoader, select_autoescape
from langchain_core.messages import HumanMessage

from src.services.llm import get_llm_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ReportData:
    """리포트 데이터"""
    case_number: str
    property_info: Dict
    rights_analysis: Dict
    valuation: Dict
    location_analysis: Dict
    risk_assessment: Dict
    bid_strategy: Dict
    generated_at: str


class ReportFormatter(ABC):
    """리포트 포맷터 기본 클래스"""

    @abstractmethod
    def format(self, data: ReportData) -> Any:
        """리포트 포맷팅"""
        pass


class JSONFormatter(ReportFormatter):
    """JSON 포맷터"""

    def format(self, data: ReportData) -> str:
        """JSON 형식 리포트 생성"""
        report = {
            "report_info": {
                "case_number": data.case_number,
                "generated_at": data.generated_at,
                "version": "1.0"
            },
            "property_summary": self._format_property(data.property_info),
            "rights_analysis": self._format_rights(data.rights_analysis),
            "valuation": self._format_valuation(data.valuation),
            "location": self._format_location(data.location_analysis),
            "risk": self._format_risk(data.risk_assessment),
            "strategy": self._format_strategy(data.bid_strategy)
        }

        return json.dumps(report, ensure_ascii=False, indent=2)

    def _format_property(self, info: Dict) -> Dict:
        """물건 정보 포맷"""
        return {
            "address": info.get("address"),
            "type": info.get("property_type"),
            "area_sqm": info.get("area_sqm"),
            "area_pyeong": round(info.get("area_sqm", 0) / 3.3058, 1) if info.get("area_sqm") else None,
            "appraisal_value": info.get("appraisal_value"),
            "minimum_bid": info.get("minimum_bid")
        }

    def _format_rights(self, analysis: Dict) -> Dict:
        """권리분석 포맷"""
        return {
            "extinction_base": analysis.get("extinction_base"),
            "assumed_rights": analysis.get("assumed_rights", []),
            "total_assumed_amount": analysis.get("total_assumed_amount", 0),
            "risk_grade": analysis.get("risk_score", {}).get("grade"),
            "red_flags": analysis.get("red_flags", [])
        }

    def _format_valuation(self, valuation: Dict) -> Dict:
        """가치평가 포맷"""
        return {
            "market_price": valuation.get("estimated_market_price"),
            "predicted_bid": valuation.get("predicted_winning_bid"),
            "predicted_bid_ratio": valuation.get("predicted_bid_ratio"),
            "confidence": valuation.get("confidence"),
            "trend_direction": valuation.get("trend_direction", "안정")
        }

    def _format_location(self, location: Dict) -> Dict:
        """입지분석 포맷"""
        score_data = location.get("score", {})
        return {
            "score": score_data.get("total"),
            "grade": score_data.get("grade"),
            "breakdown": score_data.get("breakdown", {}),
            "highlights": location.get("development", {}).get("highlights", [])
        }

    def _format_risk(self, risk: Dict) -> Dict:
        """위험평가 포맷"""
        return {
            "total_score": risk.get("total_score"),
            "grade": risk.get("grade"),
            "level": risk.get("level"),
            "red_flags": risk.get("red_flags", []),
            "beginner_friendly": risk.get("beginner_friendly", False),
            "recommendations": risk.get("recommendations", [])
        }

    def _format_strategy(self, strategy: Dict) -> Dict:
        """입찰전략 포맷"""
        recommendations = strategy.get("recommendations", [])
        return {
            "optimal_bid": strategy.get("optimal_bid"),
            "optimal_bid_rate": strategy.get("optimal_bid_rate"),
            "strategies": [
                {
                    "name": rec.get("strategy_type"),
                    "bid_price": rec.get("bid_price"),
                    "win_probability": rec.get("win_probability"),
                    "expected_roi": rec.get("expected_roi")
                }
                for rec in recommendations
            ],
            "final_recommendation": strategy.get("final_recommendation", "")
        }


class MarkdownFormatter(ReportFormatter):
    """Markdown 포맷터"""

    def __init__(self, template_dir: Optional[str] = None):
        """
        Args:
            template_dir: 템플릿 디렉토리 (None이면 기본 템플릿 사용)
        """
        self.template_dir = template_dir
        if template_dir and Path(template_dir).exists():
            self.env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            self.env = None

    def format(self, data: ReportData) -> str:
        """Markdown 형식 리포트 생성"""

        # 템플릿이 있으면 템플릿 사용
        if self.env:
            try:
                template = self.env.get_template("report_template.md.j2")
                return template.render(
                    case_number=data.case_number,
                    property=data.property_info,
                    rights=data.rights_analysis,
                    valuation=data.valuation,
                    location=data.location_analysis,
                    risk=data.risk_assessment,
                    strategy=data.bid_strategy,
                    generated_at=data.generated_at
                )
            except Exception as e:
                logger.warning(f"Template rendering failed, using default format: {e}")

        # 템플릿이 없으면 기본 포맷 사용
        return self._generate_default_markdown(data)

    def _generate_default_markdown(self, data: ReportData) -> str:
        """기본 Markdown 리포트 생성"""
        md = []

        # 헤더
        md.append("# 경매 분석 리포트\n")
        md.append(f"**사건번호**: {data.case_number}  ")
        md.append(f"**생성일**: {data.generated_at}\n")
        md.append("---\n")

        # 1. 물건 개요
        md.append("## 1. 물건 개요\n")
        prop = data.property_info
        md.append("| 항목 | 내용 |")
        md.append("|------|------|")
        md.append(f"| 소재지 | {prop.get('address', 'N/A')} |")
        md.append(f"| 물건유형 | {prop.get('property_type', 'N/A')} |")

        area_sqm = prop.get('area_sqm', 0)
        area_pyeong = round(area_sqm / 3.3058, 1) if area_sqm else 0
        md.append(f"| 면적 | {area_sqm}㎡ ({area_pyeong}평) |")

        appraisal = prop.get('appraisal_value', 0)
        min_bid = prop.get('minimum_bid', 0)
        bid_ratio = round((min_bid / appraisal * 100), 1) if appraisal else 0
        md.append(f"| 감정가 | {appraisal:,}원 |")
        md.append(f"| 최저입찰가 | {min_bid:,}원 ({bid_ratio}%) |\n")
        md.append("---\n")

        # 2. 권리분석 요약
        md.append("## 2. 권리분석 요약\n")
        rights = data.rights_analysis
        risk_grade = rights.get('risk_score', {}).get('grade', 'N/A')
        md.append(f"### 위험등급: {risk_grade}등급\n")

        extinction_base = rights.get('extinction_base', {})
        md.append("### 말소기준권리")
        md.append(f"- **유형**: {extinction_base.get('type', 'N/A')}")
        md.append(f"- **설정일**: {extinction_base.get('date', 'N/A')}\n")

        assumed_rights = rights.get('assumed_rights', [])
        md.append("### 인수해야 할 권리")
        if assumed_rights:
            md.append("| 유형 | 설정일 | 금액 |")
            md.append("|------|--------|------|")
            for r in assumed_rights:
                amount = r.get('amount', 0) or 0
                md.append(f"| {r.get('type', 'N/A')} | {r.get('date', 'N/A')} | {amount:,}원 |")

            total_assumed = rights.get('total_assumed_amount', 0)
            md.append(f"\n**총 인수금액: {total_assumed:,}원**\n")
        else:
            md.append("인수해야 할 권리가 없습니다. ✅\n")

        red_flags = rights.get('red_flags', [])
        if red_flags:
            md.append("### ⚠️ 주의사항")
            for flag in red_flags:
                md.append(f"- {flag}")
            md.append("")

        md.append("---\n")

        # 3. 가치평가 결과
        md.append("## 3. 가치평가 결과\n")
        val = data.valuation
        md.append("| 항목 | 금액/비율 |")
        md.append("|------|-----------|")
        md.append(f"| 추정 시세 | {val.get('estimated_market_price', 0):,}원 |")
        md.append(f"| 예상 낙찰가 | {val.get('predicted_winning_bid', 0):,}원 |")

        bid_ratio = val.get('predicted_bid_ratio', 0)
        md.append(f"| 예상 낙찰가율 | {bid_ratio * 100:.1f}% |")
        md.append(f"| 예측 신뢰도 | {val.get('confidence', 'N/A')} |")

        trend = val.get('trend_direction', '안정')
        md.append(f"\n### 가격 추세: {trend}\n")
        md.append("---\n")

        # 4. 입지 분석
        md.append("## 4. 입지 분석\n")
        loc = data.location_analysis
        score_data = loc.get('score', {})
        total_score = score_data.get('total', 0)
        grade = score_data.get('grade', 'N/A')
        md.append(f"### 종합 점수: {total_score}/100 ({grade}등급)\n")

        breakdown = score_data.get('breakdown', {})
        md.append("| 카테고리 | 점수 |")
        md.append("|----------|------|")
        md.append(f"| 교통 | {breakdown.get('transport', 0)} |")
        md.append(f"| 교육 | {breakdown.get('education', 0)} |")
        md.append(f"| 편의시설 | {breakdown.get('amenity', 0)} |")
        md.append(f"| 개발호재 | {breakdown.get('development', 0)} |\n")

        highlights = loc.get('development', {}).get('highlights', [])
        if highlights:
            md.append("### 개발 호재")
            for h in highlights:
                md.append(f"- {h}")
            md.append("")

        md.append("---\n")

        # 5. 위험도 평가
        md.append("## 5. 위험도 평가\n")
        risk = data.risk_assessment
        total_score = risk.get('total_score', 0)
        grade = risk.get('grade', 'N/A')
        md.append(f"### 종합 등급: {grade}등급 ({total_score}점)\n")

        beginner_friendly = risk.get('beginner_friendly', False)
        if beginner_friendly:
            md.append("🟢 **입문자 검토 가능**\n")
        else:
            md.append("🟡 **신중한 검토 필요**\n")

        md.append("| 카테고리 | 점수 | 등급 |")
        md.append("|----------|------|------|")

        for risk_type in ['rights_risk', 'market_risk', 'property_risk', 'eviction_risk']:
            risk_data = risk.get(risk_type, {})
            name = {
                'rights_risk': '권리 리스크',
                'market_risk': '시장 리스크',
                'property_risk': '물건 리스크',
                'eviction_risk': '명도 리스크'
            }[risk_type]
            score = risk_data.get('score', 0)
            level = risk_data.get('level', 'N/A')
            md.append(f"| {name} | {score} | {level} |")
        md.append("")

        red_flags = risk.get('red_flags', [])
        if red_flags:
            md.append("### 🚨 Red Flags")
            for flag in red_flags:
                flag_desc = flag if isinstance(flag, str) else flag.get('description', str(flag))
                md.append(f"- {flag_desc}")
            md.append("")

        md.append("---\n")

        # 6. 입찰 전략
        md.append("## 6. 입찰 전략\n")
        strategy = data.bid_strategy

        optimal_bid = strategy.get('optimal_bid', 0)
        optimal_rate = strategy.get('optimal_bid_rate', 0)
        md.append(f"### 최적 입찰가: {optimal_bid:,}원 ({optimal_rate * 100:.1f}%)\n")

        recommendations = strategy.get('recommendations', [])
        if recommendations:
            md.append("| 전략 | 입찰가 | 수익률 | 낙찰확률 |")
            md.append("|------|--------|--------|----------|")
            for rec in recommendations:
                name = rec.get('strategy_type', 'N/A')
                bid_price = rec.get('bid_price', 0)
                roi = rec.get('expected_roi', 0) * 100
                win_prob = rec.get('win_probability', 0) * 100
                md.append(f"| {name} | {bid_price:,}원 | {roi:.1f}% | {win_prob:.1f}% |")
            md.append("")

        final_rec = strategy.get('final_recommendation', '')
        if final_rec:
            md.append(f"### 최종 추천\n{final_rec}\n")

        md.append("---\n")

        # 7. 투자 체크리스트
        md.append("## 7. 투자 체크리스트\n")
        md.append("### 필수 확인 사항")
        md.append("- [ ] 등기부등본 최신본 확인")
        md.append("- [ ] 현장 방문 및 점유 상태 확인")
        md.append("- [ ] 인수금액 포함 총 투자금 계산")
        md.append("- [ ] 명도 가능성 검토\n")

        md.append("### 권장 확인 사항")
        md.append("- [ ] 유사 물건 실거래가 확인")
        md.append("- [ ] 임차인 배당요구 여부 확인")
        md.append("- [ ] 리모델링 필요 여부 확인\n")
        md.append("---\n")

        # 8. 최종 의견
        md.append("## 8. 최종 의견\n")
        recommendations = risk.get('recommendations', [])
        if recommendations:
            for rec in recommendations:
                md.append(f"- {rec}")
            md.append("")

        md.append("---\n")
        md.append("*본 리포트는 AI 분석 결과이며, 최종 투자 결정 시 전문가 상담을 권장합니다.*\n")

        return "\n".join(md)


class HTMLFormatter(ReportFormatter):
    """HTML 포맷터"""

    def __init__(self, template_dir: Optional[str] = None):
        """
        Args:
            template_dir: 템플릿 디렉토리
        """
        self.template_dir = template_dir
        if template_dir and Path(template_dir).exists():
            self.env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            self.env = None

        self.markdown_formatter = MarkdownFormatter(template_dir)

    def format(self, data: ReportData) -> str:
        """HTML 형식 리포트 생성"""

        # 템플릿이 있으면 템플릿 사용
        if self.env:
            try:
                template = self.env.get_template("email_template.html.j2")
                return template.render(
                    case_number=data.case_number,
                    property=data.property_info,
                    rights=data.rights_analysis,
                    valuation=data.valuation,
                    location=data.location_analysis,
                    risk=data.risk_assessment,
                    strategy=data.bid_strategy,
                    generated_at=data.generated_at
                )
            except Exception as e:
                logger.warning(f"HTML template rendering failed, converting from markdown: {e}")

        # Markdown을 HTML로 변환
        md_content = self.markdown_formatter.format(data)

        try:
            import markdown
            html_body = markdown.markdown(
                md_content,
                extensions=['tables', 'fenced_code', 'nl2br']
            )
        except ImportError:
            # markdown 패키지가 없으면 간단한 변환
            html_body = md_content.replace('\n', '<br>\n')

        # HTML 래핑
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>경매 분석 리포트 - {data.case_number}</title>
    <style>
        body {{
            font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        h3 {{
            color: #546e7a;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .warning {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .success {{
            color: #27ae60;
            font-weight: bold;
        }}
        .info {{
            background-color: #e3f2fd;
            padding: 15px;
            border-left: 4px solid #2196f3;
            margin: 15px 0;
        }}
        hr {{
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_body}
    </div>
</body>
</html>"""

        return html


class ExplanationGenerator:
    """LLM 기반 설명 생성기"""

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 기본 클라이언트 사용)
        """
        self.llm = llm_client or get_llm_client()

    async def generate_beginner_explanation(self, data: ReportData) -> str:
        """입문자용 쉬운 설명 생성"""

        prompt = f"""경매 입문자가 이해할 수 있도록 다음 분석 결과를 쉽게 설명해주세요.

## 물건 정보
- 주소: {data.property_info.get('address', 'N/A')}
- 감정가: {data.property_info.get('appraisal_value', 0):,}원
- 최저입찰가: {data.property_info.get('minimum_bid', 0):,}원

## 분석 결과
- 위험등급: {data.risk_assessment.get('grade', 'N/A')}
- 인수금액: {data.rights_analysis.get('total_assumed_amount', 0):,}원
- 추정 시세: {data.valuation.get('estimated_market_price', 0):,}원
- 최적 입찰가: {data.bid_strategy.get('optimal_bid', 0):,}원

비유와 예시를 사용하여 200자 내외로 설명해주세요.
전문 용어는 피하고, 일상적인 언어로 핵심만 전달해주세요."""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate beginner explanation: {e}")
            return "리포트 생성 중 오류가 발생했습니다. 상세 내용은 전체 리포트를 참고해주세요."

    async def generate_executive_summary(self, data: ReportData) -> str:
        """핵심 요약 생성"""

        recommendations = data.bid_strategy.get('recommendations', [])
        expected_roi = 0
        if recommendations and len(recommendations) > 1:
            expected_roi = recommendations[1].get('expected_roi', 0) * 100

        red_flags_count = len(data.risk_assessment.get('red_flags', []))

        prompt = f"""다음 경매 분석 결과의 핵심만 3줄로 요약해주세요.

- 사건번호: {data.case_number}
- 위험등급: {data.risk_assessment.get('grade', 'N/A')}
- 인수금액: {data.rights_analysis.get('total_assumed_amount', 0):,}원
- 예상수익률: {expected_roi:.1f}%
- Red Flags: {red_flags_count}개

형식:
1. 물건 상태: ...
2. 핵심 리스크: ...
3. 투자 의견: ..."""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            return f"사건번호 {data.case_number}의 분석이 완료되었습니다. 상세 내용은 전체 리포트를 참고해주세요."


class ChartGenerator:
    """차트 생성기"""

    def generate_risk_radar(self, risk_data: Dict) -> Optional[bytes]:
        """위험도 레이더 차트 생성"""
        try:
            import plotly.graph_objects as go

            categories = ['권리', '시장', '물건', '명도']
            values = [
                risk_data.get('rights_risk', {}).get('score', 0),
                risk_data.get('market_risk', {}).get('score', 0),
                risk_data.get('property_risk', {}).get('score', 0),
                risk_data.get('eviction_risk', {}).get('score', 0)
            ]

            fig = go.Figure()

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='위험도',
                line=dict(color='#e74c3c')
            ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )
                ),
                showlegend=False,
                title="위험도 분포",
                font=dict(family="Malgun Gothic")
            )

            return fig.to_image(format="png", engine="kaleido")
        except Exception as e:
            logger.warning(f"Failed to generate risk radar chart: {e}")
            return None

    def generate_bid_comparison(self, strategies: list) -> Optional[bytes]:
        """입찰 전략 비교 차트 생성"""
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            if not strategies:
                return None

            names = [s.get('strategy_type', 'N/A') for s in strategies]
            bid_prices = [s.get('bid_price', 0) / 100000000 for s in strategies]  # 억 단위
            roi = [s.get('expected_roi', 0) * 100 for s in strategies]
            win_prob = [s.get('win_probability', 0) * 100 for s in strategies]

            fig = make_subplots(
                rows=1, cols=3,
                subplot_titles=('입찰가 (억원)', '예상 수익률 (%)', '낙찰 확률 (%)')
            )

            colors = ['#27ae60', '#f39c12', '#e74c3c']

            fig.add_trace(
                go.Bar(x=names, y=bid_prices, marker_color=colors, name='입찰가'),
                row=1, col=1
            )

            fig.add_trace(
                go.Bar(x=names, y=roi, marker_color=colors, name='수익률'),
                row=1, col=2
            )

            fig.add_trace(
                go.Bar(x=names, y=win_prob, marker_color=colors, name='낙찰 확률'),
                row=1, col=3
            )

            fig.update_layout(
                showlegend=False,
                height=400,
                font=dict(family="Malgun Gothic")
            )

            return fig.to_image(format="png", engine="kaleido")
        except Exception as e:
            logger.warning(f"Failed to generate bid comparison chart: {e}")
            return None

    def generate_price_trend(self, trend_data: List[float]) -> Optional[bytes]:
        """가격 추세 차트 생성"""
        try:
            import plotly.graph_objects as go

            months = ['1개월', '2개월', '3개월', '4개월', '5개월', '6개월']
            values = trend_data[:6] if trend_data else [0] * 6

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=months,
                y=values,
                mode='lines+markers',
                line=dict(color='#3498db', width=3),
                marker=dict(size=10),
                name='가격 추세'
            ))

            fig.update_layout(
                title="향후 6개월 가격 추세 예측",
                xaxis_title="",
                yaxis_title="변동률 (%)",
                height=300,
                font=dict(family="Malgun Gothic")
            )

            return fig.to_image(format="png", engine="kaleido")
        except Exception as e:
            logger.warning(f"Failed to generate price trend chart: {e}")
            return None


class ReporterAgent:
    """리포터 에이전트 - 분석 결과를 종합하여 리포트 생성"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: 에이전트 설정
                - template_dir: 템플릿 디렉토리 경로
                - enable_charts: 차트 생성 여부 (기본: True)
                - enable_llm_explanation: LLM 설명 생성 여부 (기본: True)
        """
        config = config or {}
        template_dir = config.get('template_dir')

        self.json_formatter = JSONFormatter()
        self.markdown_formatter = MarkdownFormatter(template_dir)
        self.html_formatter = HTMLFormatter(template_dir)

        self.enable_charts = config.get('enable_charts', True)
        self.enable_llm_explanation = config.get('enable_llm_explanation', True)

        if self.enable_charts:
            self.chart_generator = ChartGenerator()

        if self.enable_llm_explanation:
            self.explanation_generator = ExplanationGenerator()

        logger.info("ReporterAgent initialized")

    async def generate(
        self,
        case_number: str,
        rights_analysis: Dict,
        location_analysis: Dict,
        valuation: Dict,
        risk_assessment: Dict,
        bid_strategy: Dict,
        property_info: Optional[Dict] = None,
        output_formats: List[str] = None
    ) -> Dict:
        """리포트 생성

        Args:
            case_number: 사건번호
            rights_analysis: 권리분석 결과
            location_analysis: 입지분석 결과
            valuation: 가치평가 결과
            risk_assessment: 위험평가 결과
            bid_strategy: 입찰전략 결과
            property_info: 물건 정보 (None이면 valuation에서 추출)
            output_formats: 출력 형식 리스트 (기본: ["json", "markdown"])

        Returns:
            리포트 데이터
        """
        if output_formats is None:
            output_formats = ["json", "markdown"]

        logger.info(f"Generating report for case {case_number}")

        # 데이터 준비
        report_data = ReportData(
            case_number=case_number,
            property_info=property_info or valuation.get("property_info", {}),
            rights_analysis=rights_analysis,
            valuation=valuation,
            location_analysis=location_analysis,
            risk_assessment=risk_assessment,
            bid_strategy=bid_strategy,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        result = {
            "case_number": case_number,
            "generated_at": report_data.generated_at,
            "outputs": {}
        }

        # 포맷별 생성
        try:
            if "json" in output_formats:
                logger.debug("Generating JSON format")
                result["outputs"]["json"] = self.json_formatter.format(report_data)

            if "markdown" in output_formats:
                logger.debug("Generating Markdown format")
                result["outputs"]["markdown"] = self.markdown_formatter.format(report_data)

            if "html" in output_formats:
                logger.debug("Generating HTML format")
                result["outputs"]["html"] = self.html_formatter.format(report_data)

        except Exception as e:
            logger.error(f"Error generating report formats: {e}")
            raise

        # 차트 생성
        if self.enable_charts:
            logger.debug("Generating charts")
            result["charts"] = {}

            risk_radar = self.chart_generator.generate_risk_radar(risk_assessment)
            if risk_radar:
                result["charts"]["risk_radar"] = risk_radar

            bid_comparison = self.chart_generator.generate_bid_comparison(
                bid_strategy.get("recommendations", [])
            )
            if bid_comparison:
                result["charts"]["bid_comparison"] = bid_comparison

        # LLM 설명 생성
        if self.enable_llm_explanation:
            logger.debug("Generating LLM explanations")
            result["explanations"] = {}

            try:
                beginner_exp = await self.explanation_generator.generate_beginner_explanation(report_data)
                result["explanations"]["beginner"] = beginner_exp
            except Exception as e:
                logger.warning(f"Failed to generate beginner explanation: {e}")
                result["explanations"]["beginner"] = "설명 생성 실패"

            try:
                summary = await self.explanation_generator.generate_executive_summary(report_data)
                result["explanations"]["summary"] = summary
            except Exception as e:
                logger.warning(f"Failed to generate executive summary: {e}")
                result["explanations"]["summary"] = "요약 생성 실패"

        logger.info(f"Report generation completed for case {case_number}")
        return result

    async def save_report(
        self,
        report: Dict,
        output_dir: str
    ) -> Dict[str, str]:
        """리포트 파일 저장

        Args:
            report: generate()로 생성한 리포트
            output_dir: 출력 디렉토리

        Returns:
            저장된 파일 경로 딕셔너리
        """
        case_number = report["case_number"]
        output_path = Path(output_dir) / case_number
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = {}

        try:
            # JSON 저장
            if "json" in report["outputs"]:
                json_path = output_path / "report.json"
                json_path.write_text(report["outputs"]["json"], encoding="utf-8")
                saved_files["json"] = str(json_path)
                logger.debug(f"Saved JSON report to {json_path}")

            # Markdown 저장
            if "markdown" in report["outputs"]:
                md_path = output_path / "report.md"
                md_path.write_text(report["outputs"]["markdown"], encoding="utf-8")
                saved_files["markdown"] = str(md_path)
                logger.debug(f"Saved Markdown report to {md_path}")

            # HTML 저장
            if "html" in report["outputs"]:
                html_path = output_path / "report.html"
                html_path.write_text(report["outputs"]["html"], encoding="utf-8")
                saved_files["html"] = str(html_path)
                logger.debug(f"Saved HTML report to {html_path}")

            # 차트 저장
            if "charts" in report:
                charts_dir = output_path / "charts"
                charts_dir.mkdir(exist_ok=True)

                for chart_name, chart_data in report["charts"].items():
                    if chart_data:
                        chart_path = charts_dir / f"{chart_name}.png"
                        chart_path.write_bytes(chart_data)
                        saved_files[f"chart_{chart_name}"] = str(chart_path)
                        logger.debug(f"Saved chart to {chart_path}")

        except Exception as e:
            logger.error(f"Error saving report files: {e}")
            raise

        logger.info(f"Report files saved to {output_path}")
        return saved_files

    def generate_sync(
        self,
        case_number: str,
        rights_analysis: Dict,
        location_analysis: Dict,
        valuation: Dict,
        risk_assessment: Dict,
        bid_strategy: Dict,
        property_info: Optional[Dict] = None,
        output_formats: List[str] = None
    ) -> Dict:
        """동기 버전의 리포트 생성 (LLM 설명 제외)

        LLM 설명이 필요 없는 경우 사용하는 동기 버전
        """
        if output_formats is None:
            output_formats = ["json", "markdown"]

        logger.info(f"Generating report (sync) for case {case_number}")

        # 데이터 준비
        report_data = ReportData(
            case_number=case_number,
            property_info=property_info or valuation.get("property_info", {}),
            rights_analysis=rights_analysis,
            valuation=valuation,
            location_analysis=location_analysis,
            risk_assessment=risk_assessment,
            bid_strategy=bid_strategy,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        result = {
            "case_number": case_number,
            "generated_at": report_data.generated_at,
            "outputs": {}
        }

        # 포맷별 생성
        if "json" in output_formats:
            result["outputs"]["json"] = self.json_formatter.format(report_data)

        if "markdown" in output_formats:
            result["outputs"]["markdown"] = self.markdown_formatter.format(report_data)

        if "html" in output_formats:
            result["outputs"]["html"] = self.html_formatter.format(report_data)

        # 차트 생성
        if self.enable_charts:
            result["charts"] = {}

            risk_radar = self.chart_generator.generate_risk_radar(risk_assessment)
            if risk_radar:
                result["charts"]["risk_radar"] = risk_radar

            bid_comparison = self.chart_generator.generate_bid_comparison(
                bid_strategy.get("recommendations", [])
            )
            if bid_comparison:
                result["charts"]["bid_comparison"] = bid_comparison

        logger.info(f"Report generation (sync) completed for case {case_number}")
        return result
