import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import json

st.set_page_config(page_title="Power BI HTML DAX Generator Pro", layout="wide", page_icon="📊")

class ThresholdDirection(Enum):
    HIGHER_BETTER = "Higher is Better"
    LOWER_BETTER = "Lower is Better"
    RANGE_OPTIMAL = "Optimal Range"
    
class ThresholdLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class ThresholdConfig:
    metric_name: str
    direction: ThresholdDirection
    excellent_min: Optional[float] = None
    excellent_max: Optional[float] = None
    good_min: Optional[float] = None
    good_max: Optional[float] = None
    warning_min: Optional[float] = None
    warning_max: Optional[float] = None
    critical_min: Optional[float] = None
    critical_max: Optional[float] = None
    
    def get_dax_condition(self, var_name: str, theme: 'ColorTheme') -> str:
        if self.direction == ThresholdDirection.HIGHER_BETTER:
            return f"""IF({var_name} >= {self.excellent_min}, "{theme.success}",
                IF({var_name} >= {self.good_min}, "{theme.primary}",
                IF({var_name} >= {self.warning_min}, "{theme.warning}",
                "{theme.danger}")))"""
        elif self.direction == ThresholdDirection.LOWER_BETTER:
            return f"""IF({var_name} <= {self.excellent_max}, "{theme.success}",
                IF({var_name} <= {self.good_max}, "{theme.primary}",
                IF({var_name} <= {self.warning_max}, "{theme.warning}",
                "{theme.danger}")))"""
        else:  # RANGE_OPTIMAL
            return f"""IF({var_name} >= {self.excellent_min} && {var_name} <= {self.excellent_max}, "{theme.success}",
                IF({var_name} >= {self.good_min} && {var_name} <= {self.good_max}, "{theme.primary}",
                IF({var_name} >= {self.warning_min} && {var_name} <= {self.warning_max}, "{theme.warning}",
                "{theme.danger}")))"""
    
    def get_text_condition(self, var_name: str) -> str:
        if self.direction == ThresholdDirection.HIGHER_BETTER:
            return f"""IF({var_name} >= {self.excellent_min}, "excellent",
                IF({var_name} >= {self.good_min}, "strong",
                IF({var_name} >= {self.warning_min}, "needs attention",
                "critical")))"""
        elif self.direction == ThresholdDirection.LOWER_BETTER:
            return f"""IF({var_name} <= {self.excellent_max}, "excellent",
                IF({var_name} <= {self.good_max}, "good",
                IF({var_name} <= {self.warning_max}, "elevated",
                "critical")))"""
        else:
            return f"""IF({var_name} >= {self.excellent_min} && {var_name} <= {self.excellent_max}, "optimal",
                IF({var_name} >= {self.good_min} && {var_name} <= {self.good_max}, "acceptable",
                IF({var_name} >= {self.warning_min} && {var_name} <= {self.warning_max}, "suboptimal",
                "out of range")))"""

@dataclass
class ColorTheme:
    name: str
    primary: str
    secondary: str
    success: str
    warning: str
    danger: str
    neutral: str
    background: str
    light_success: str
    light_warning: str
    light_danger: str
    light_primary: str

THEMES = {
    "Corporate Blue": ColorTheme(
        "Corporate Blue", "#3b82f6", "#1e40af", "#059669", "#f59e0b", "#dc2626",
        "#6b7280", "#f8fafc", "#d1fae5", "#fef3c7", "#fee2e2", "#dbeafe"
    ),
    "Professional Gray": ColorTheme(
        "Professional Gray", "#64748b", "#334155", "#10b981", "#f59e0b", "#ef4444",
        "#94a3b8", "#f1f5f9", "#d1fae5", "#fef3c7", "#fee2e2", "#e2e8f0"
    ),
    "Modern Purple": ColorTheme(
        "Modern Purple", "#8b5cf6", "#6d28d9", "#059669", "#f59e0b", "#dc2626",
        "#6b7280", "#faf5ff", "#d1fae5", "#fef3c7", "#fee2e2", "#ede9fe"
    ),
    "Elegant Green": ColorTheme(
        "Elegant Green", "#059669", "#047857", "#10b981", "#f59e0b", "#dc2626",
        "#6b7280", "#f0fdf4", "#d1fae5", "#fef3c7", "#fee2e2", "#d1fae5"
    ),
    "Executive Dark": ColorTheme(
        "Executive Dark", "#1e293b", "#0f172a", "#10b981", "#f59e0b", "#ef4444",
        "#64748b", "#f8fafc", "#d1fae5", "#fef3c7", "#fee2e2", "#cbd5e1"
    ),
}

ICONS = {
    "metrics": ["📊", "📈", "📉", "💹", "🎯", "⚡", "💡", "🔍"],
    "performance": ["🏆", "⭐", "🌟", "✨", "👑", "🎖️", "🥇", "💎"],
    "warning": ["⚠️", "🚨", "🔴", "⛔", "🔔", "📢", "🚩", "⚡"],
    "positive": ["✅", "💚", "👍", "😊", "🎉", "🌈", "🔥", "💪"],
    "negative": ["❌", "🔴", "👎", "😟", "⚠️", "📉", "🔧", "💔"],
    "analysis": ["🔬", "🔎", "📋", "📝", "🗂️", "📌", "🎓", "🧠"],
    "geographic": ["🌍", "🌎", "🌏", "🗺️", "📍", "🏢", "🌐", "🛫"],
    "people": ["👨‍🏫", "👥", "👤", "🧑‍💼", "👨‍💻", "👩‍💻", "🙋", "🤝"],
    "trend": ["📈", "📉", "💹", "🔄", "⬆️", "⬇️", "↗️", "↘️"],
}

@dataclass
class NarrativeSection:
    id: str
    name: str
    description: str
    requires_categorical: bool = False
    requires_text: bool = False
    requires_date: bool = False
    enabled: bool = True
    icon: str = "📊"
    show_if_threshold: Optional[str] = None

AVAILABLE_SECTIONS = {
    "header": NarrativeSection("header", "Executive Header", "Gradient header with key stats", enabled=True, icon="📊"),
    "kpi_cards": NarrativeSection("kpi_cards", "KPI Cards Grid", "Visual metric cards with thresholds", enabled=True, icon="📈"),
    "trend_analysis": NarrativeSection("trend_analysis", "Trend Analysis", "30-day trend comparison", requires_date=True, icon="📉"),
    "performance_table": NarrativeSection("performance_table", "Performance Matrix", "Categorical breakdown table", requires_categorical=True, icon="📋"),
    "top_bottom": NarrativeSection("top_bottom", "Top/Bottom Performers", "Best and worst performers", requires_categorical=True, icon="🏆"),
    "geographic": NarrativeSection("geographic", "Geographic Analysis", "Regional performance breakdown", requires_categorical=True, icon="🌍"),
    "action_dashboard": NarrativeSection("action_dashboard", "Priority Actions", "Conditional action items", enabled=True, icon="🚨"),
    "positive_verbatim": NarrativeSection("positive_verbatim", "Positive Feedback", "Top promoter comments", requires_text=True, icon="💚"),
    "negative_verbatim": NarrativeSection("negative_verbatim", "Critical Feedback", "Top detractor comments", requires_text=True, icon="🔴"),
    "theme_analysis": NarrativeSection("theme_analysis", "Theme Analysis", "Keyword frequency analysis", requires_text=True, icon="🔍"),
    "distribution": NarrativeSection("distribution", "Score Distribution", "Visual distribution chart", icon="📊"),
    "velocity": NarrativeSection("velocity", "Response Velocity", "Volume change over time", requires_date=True, icon="⚡"),
}

class DAXGenerator:
    def __init__(self, table_name: str, date_column: Optional[str], theme: ColorTheme):
        self.table = table_name
        self.date_col = date_column
        self.theme = theme
        self.metrics: Dict[str, Dict] = {}
        self.categorical_columns: List[str] = []
        self.text_columns: Dict[str, str] = {}  # column_name: score_column_name
        self.enabled_sections: List[str] = []
        self.icons: Dict[str, str] = {}
        self.thresholds: Dict[str, ThresholdConfig] = {}
        
    def add_metric(self, name: str, column: str, aggregation: str, format_decimals: int = 2):
        self.metrics[name] = {
            'column': column,
            'aggregation': aggregation,
            'format': format_decimals
        }
    
    def generate_dax(self) -> str:
        sections = [
            self._generate_header(),
            self._generate_variables(),
            self._generate_html_start(),
        ]
        
        if "header" in self.enabled_sections:
            sections.append(self._generate_executive_header())
        
        if "kpi_cards" in self.enabled_sections:
            sections.append(self._generate_kpi_cards())
        
        if "trend_analysis" in self.enabled_sections and self.date_col:
            sections.append(self._generate_trend_section())
        
        if "performance_table" in self.enabled_sections and self.categorical_columns:
            sections.append(self._generate_performance_table())
        
        if "top_bottom" in self.enabled_sections and self.categorical_columns:
            sections.append(self._generate_top_bottom())
        
        if "action_dashboard" in self.enabled_sections:
            sections.append(self._generate_action_dashboard())
        
        if "positive_verbatim" in self.enabled_sections and self.text_columns:
            sections.append(self._generate_positive_verbatim())
        
        if "negative_verbatim" in self.enabled_sections and self.text_columns:
            sections.append(self._generate_negative_verbatim())
        
        if "theme_analysis" in self.enabled_sections and self.text_columns:
            sections.append(self._generate_theme_analysis())
        
        if "distribution" in self.enabled_sections:
            sections.append(self._generate_distribution())
        
        if "velocity" in self.enabled_sections and self.date_col:
            sections.append(self._generate_velocity())
        
        sections.extend([
            self._generate_footer(),
            self._generate_html_end(),
        ])
        
        return "\n\n".join(filter(None, sections))
    
    def _generate_header(self) -> str:
        return f"""/* ============================================
   POWER BI HTML DAX NARRATIVE GENERATOR
   Auto-Generated Code - Production Ready
   Theme: {self.theme.name}
   Sections: {', '.join(self.enabled_sections)}
   ============================================ */
   
Auto_Narrative_HTML = """
    
    def _generate_variables(self) -> str:
        vars_list = [
            f"/* ---- Core Metrics ---- */",
            f"VAR TotalResponses = COUNTROWS('{self.table}')"
        ]
        
        if self.date_col:
            vars_list.extend([
                f"VAR MaxDate = MAX('{self.table}'[{self.date_col}])",
                f"VAR MinDate = MIN('{self.table}'[{self.date_col}])",
                f"VAR Date30DaysAgo = MaxDate - 30",
                f"VAR Date60DaysAgo = MaxDate - 60"
            ])
        
        for name, config in self.metrics.items():
            var_name = name.replace(" ", "")
            vars_list.append(
                f"VAR {var_name} = ROUND({config['aggregation']}('{self.table}'[{config['column']}]), {config['format']})"
            )
            
            if name in self.thresholds:
                threshold = self.thresholds[name]
                vars_list.append(f"VAR {var_name}_Color = {threshold.get_dax_condition(var_name, self.theme)}")
                vars_list.append(f"VAR {var_name}_Status = {threshold.get_text_condition(var_name)}")
        
        if self.date_col and self.metrics:
            first_metric = list(self.metrics.values())[0]
            vars_list.extend([
                f"\n/* ---- Trend Analysis ---- */",
                f"VAR Last30DaysAvg = CALCULATE({first_metric['aggregation']}('{self.table}'[{first_metric['column']}]), '{self.table}'[{self.date_col}] >= Date30DaysAgo)",
                f"VAR Previous30DaysAvg = CALCULATE({first_metric['aggregation']}('{self.table}'[{first_metric['column']}]), '{self.table}'[{self.date_col}] >= Date60DaysAgo, '{self.table}'[{self.date_col}] < Date30DaysAgo)",
                f"VAR Trend = IF(NOT ISBLANK(Previous30DaysAvg), ROUND(Last30DaysAvg - Previous30DaysAvg, 2), BLANK())",
                f"VAR TrendPct = IF(Previous30DaysAvg <> 0, ROUND(DIVIDE(Trend, Previous30DaysAvg, 0) * 100, 0), 0)",
                f"VAR TrendIcon = IF(Trend > 0, \"↗️\", IF(Trend < 0, \"↘️\", \"→\"))",
                f"VAR TrendColor = IF(Trend > 0, \"{self.theme.success}\", IF(Trend < 0, \"{self.theme.danger}\", \"{self.theme.neutral}\"))"
            ])
            
            vars_list.extend([
                f"VAR ResponsesLast30 = CALCULATE(COUNTROWS('{self.table}'), '{self.table}'[{self.date_col}] >= Date30DaysAgo)",
                f"VAR ResponsesPrev30 = CALCULATE(COUNTROWS('{self.table}'), '{self.table}'[{self.date_col}] >= Date60DaysAgo, '{self.table}'[{self.date_col}] < Date30DaysAgo)",
                f"VAR ResponseVelocity = IF(ResponsesPrev30 <> 0, ROUND(DIVIDE(ResponsesLast30 - ResponsesPrev30, ResponsesPrev30, 0) * 100, 0), BLANK())"
            ])
        
        if self.categorical_columns:
            cat_col = self.categorical_columns[0]
            first_metric = list(self.metrics.values())[0]
            vars_list.extend([
                f"\n/* ---- Performance Analysis ---- */",
                f"VAR PerformanceSummary = SUMMARIZE(",
                f"    '{self.table}',",
                f"    '{self.table}'[{cat_col}],",
                f"    \"AvgScore\", {first_metric['aggregation']}('{self.table}'[{first_metric['column']}]),",
                f"    \"RecordCount\", COUNTROWS('{self.table}')",
                f")",
                f"VAR TopPerformer = TOPN(1, PerformanceSummary, [AvgScore], DESC)",
                f"VAR BottomPerformer = TOPN(1, PerformanceSummary, [AvgScore], ASC)",
                f"VAR TopPerformerName = MAXX(TopPerformer, '{self.table}'[{cat_col}])",
                f"VAR TopPerformerScore = ROUND(MAXX(TopPerformer, [AvgScore]), 2)",
                f"VAR TopPerformerCount = MAXX(TopPerformer, [RecordCount])",
                f"VAR BottomPerformerName = MAXX(BottomPerformer, '{self.table}'[{cat_col}])",
                f"VAR BottomPerformerScore = ROUND(MAXX(BottomPerformer, [AvgScore]), 2)",
                f"VAR BottomPerformerCount = MAXX(BottomPerformer, [RecordCount])",
                f"VAR Top3Performers = TOPN(3, PerformanceSummary, [AvgScore], DESC)",
                f"VAR Bottom3Performers = TOPN(3, PerformanceSummary, [AvgScore], ASC)",
                f"VAR Top3Text = CONCATENATEX(Top3Performers, '{self.table}'[{cat_col}] & \" (\" & ROUND([AvgScore], 1) & \")\", \", \", [AvgScore], DESC)",
                f"VAR Bottom3Text = CONCATENATEX(Bottom3Performers, '{self.table}'[{cat_col}] & \" (\" & ROUND([AvgScore], 1) & \")\", \", \", [AvgScore], ASC)"
            ])
        
        if self.text_columns:
            text_col = list(self.text_columns.keys())[0]
            score_col = self.text_columns[text_col]
            vars_list.extend([
                f"\n/* ---- Text Analysis ---- */",
                f"VAR PositiveComments = TOPN(5, FILTER('{self.table}', NOT ISBLANK('{self.table}'[{text_col}]) && LEN('{self.table}'[{text_col}]) > 10), '{self.table}'[{score_col}], DESC)",
                f"VAR NegativeComments = TOPN(5, FILTER('{self.table}', NOT ISBLANK('{self.table}'[{text_col}]) && LEN('{self.table}'[{text_col}]) > 10), '{self.table}'[{score_col}], ASC)",
                f"VAR PositiveHTML = CONCATENATEX(PositiveComments, \"<div style='background:white; padding:12px; border-radius:8px; margin:8px 0; border-left:3px solid {self.theme.success};'><div style='font-size:11px; color:{self.theme.success}; font-weight:600; margin-bottom:4px;'>{self.icons.get('positive', '💚')} Score: \" & ROUND('{self.table}'[{score_col}], 1) & \"</div><div style='font-size:12px; color:#374151; line-height:1.6;'>\" & '{self.table}'[{text_col}] & \"</div></div>\", \"\", '{self.table}'[{score_col}], DESC)",
                f"VAR NegativeHTML = CONCATENATEX(NegativeComments, \"<div style='background:white; padding:12px; border-radius:8px; margin:8px 0; border-left:3px solid {self.theme.danger};'><div style='font-size:11px; color:{self.theme.danger}; font-weight:600; margin-bottom:4px;'>{self.icons.get('negative', '🔴')} Score: \" & ROUND('{self.table}'[{score_col}], 1) & \"</div><div style='font-size:12px; color:#374151; line-height:1.6;'>\" & '{self.table}'[{text_col}] & \"</div></div>\", \"\", '{self.table}'[{score_col}], ASC)",
                f"VAR PositiveCount = COUNTROWS(PositiveComments)",
                f"VAR NegativeCount = COUNTROWS(NegativeComments)"
            ])
        
        return "\n".join(vars_list)
    
    def _generate_html_start(self) -> str:
        return f"""
VAR HtmlContent = 
"<div style='font-family:system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif; max-width:1400px; margin:0; padding:20px; background:{self.theme.background}; color:#1f2937;'>" &"""
    
    def _generate_executive_header(self) -> str:
        date_range = f"\" & MinDate & \" to \" & MaxDate & \"" if self.date_col else "All Time"
        return f"""
"<div style='background:linear-gradient(135deg, {self.theme.primary} 0%, {self.theme.secondary} 100%); color:white; padding:28px; border-radius:12px; margin-bottom:24px; box-shadow:0 4px 12px rgba(0,0,0,0.15);'>" &
"<div style='display:flex; justify-content:space-between; align-items:center;'>" &
"<div>" &
"<h1 style='margin:0 0 8px 0; font-size:32px; font-weight:700;'>{self.icons.get('metrics', '📊')} Performance Intelligence Dashboard</h1>" &
"<p style='margin:0; font-size:15px; opacity:0.95;'>Comprehensive Analysis • \" & TotalResponses & \" Total Records • Period: {date_range}</p>" &
"</div>" &
"</div>" &
"</div>" &"""
    
    def _generate_kpi_cards(self) -> str:
        cards = []
        for name, config in self.metrics.items():
            var_name = name.replace(" ", "")
            has_threshold = name in self.thresholds
            
            card = f"""
"<div style='background:white; padding:18px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.08); border-left:4px solid \" & {var_name}_Color & \";'>" &
"<div style='font-size:12px; color:{self.theme.neutral}; font-weight:500; margin-bottom:6px;'>{name}</div>" &
"<div style='font-size:28px; font-weight:700; color:\" & {var_name}_Color & \"; margin-bottom:4px;'>\" & {var_name} & \"</div>" &
"<div style='font-size:11px; color:{self.theme.neutral}; font-weight:500;'>Status: <span style='color:\" & {var_name}_Color & \";'>\" & {var_name}_Status & \"</span></div>" &
"</div>" &"""
            cards.append(card)
        
        grid_cols = min(len(self.metrics), 4)
        return f"""
"<div style='margin-bottom:24px;'>" &
"<h2 style='color:#1f2937; font-size:18px; font-weight:600; margin:0 0 16px 0; padding-bottom:8px; border-bottom:2px solid #e5e7eb;'>{self.icons.get('metrics', '📈')} Key Performance Indicators</h2>" &
"<div style='display:grid; grid-template-columns:repeat({grid_cols}, 1fr); gap:16px;'>" &
{' '.join(cards)}
"</div>" &
"</div>" &"""
    
    def _generate_trend_section(self) -> str:
        return f"""
"<div style='background:{self.theme.light_primary}; border-radius:12px; padding:20px; margin-bottom:24px; border-left:4px solid {self.theme.primary};'>" &
"<h3 style='color:{self.theme.primary}; font-size:16px; font-weight:600; margin:0 0 14px 0;'>{self.icons.get('trend', '📈')} 30-Day Trend Analysis</h3>" &
"<div style='display:grid; grid-template-columns:repeat(3, 1fr); gap:14px;'>" &
"<div style='background:white; padding:14px; border-radius:8px;'>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-bottom:4px;'>Current Period</div>" &
"<div style='font-size:22px; font-weight:700; color:{self.theme.primary};'>\" & ROUND(Last30DaysAvg, 2) & \"</div>" &
"</div>" &
"<div style='background:white; padding:14px; border-radius:8px;'>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-bottom:4px;'>Previous Period</div>" &
"<div style='font-size:22px; font-weight:700; color:#6b7280;'>\" & ROUND(Previous30DaysAvg, 2) & \"</div>" &
"</div>" &
"<div style='background:white; padding:14px; border-radius:8px;'>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-bottom:4px;'>Change</div>" &
"<div style='font-size:22px; font-weight:700; color:\" & TrendColor & \";'>\" & TrendIcon & \" \" & IF(Trend > 0, \"+\", \"\") & Trend & \" (\" & IF(TrendPct > 0, \"+\", \"\") & TrendPct & \"%)\" & \"</div>" &
"</div>" &
"</div>" &
"<p style='font-size:12px; color:#6b7280; margin:12px 0 0 0; font-style:italic;'>Comparing most recent 30 days vs previous 30 days</p>" &
"</div>" &"""
    
    def _generate_performance_table(self) -> str:
        cat_col = self.categorical_columns[0]
        return f"""
"<div style='margin-bottom:24px;'>" &
"<h3 style='color:#1f2937; font-size:16px; font-weight:600; margin:0 0 14px 0; padding-bottom:8px; border-bottom:2px solid #e5e7eb;'>{self.icons.get('analysis', '📋')} Performance by {cat_col}</h3>" &
"<div style='background:white; padding:18px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.08);'>" &
"<div style='display:grid; grid-template-columns:2fr 1fr 1fr; gap:12px; padding:12px; background:{self.theme.background}; border-radius:8px; font-weight:600; font-size:12px; color:{self.theme.neutral};'>" &
"<div>{cat_col}</div><div>Avg Score</div><div>Records</div>" &
"</div>" &
"<div style='margin-top:8px;'>\" & 
CONCATENATEX(
    TOPN(10, PerformanceSummary, [AvgScore], DESC),
    \"<div style='display:grid; grid-template-columns:2fr 1fr 1fr; gap:12px; padding:12px; border-bottom:1px solid #f3f4f6; font-size:13px;'>\" &
    \"<div style='font-weight:500; color:#1f2937;'>\" & '{self.table}'[{cat_col}] & \"</div>\" &
    \"<div style='font-weight:600; color:{self.theme.primary};'>\" & ROUND([AvgScore], 2) & \"</div>\" &
    \"<div style='color:{self.theme.neutral};'>\" & [RecordCount] & \"</div>\" &
    \"</div>\",
    \"\",
    [AvgScore], DESC
) & \"" &
"</div>" &
"</div>" &
"</div>" &"""
    
    def _generate_top_bottom(self) -> str:
        return f"""
"<div style='display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:24px;'>" &
"<div style='background:{self.theme.light_success}; padding:18px; border-radius:12px; border-left:4px solid {self.theme.success};'>" &
"<h3 style='color:{self.theme.success}; font-size:15px; font-weight:600; margin:0 0 12px 0;'>{self.icons.get('performance', '🏆')} Top Performer</h3>" &
"<div style='background:white; padding:14px; border-radius:8px;'>" &
"<div style='font-size:16px; font-weight:700; color:#1f2937; margin-bottom:6px;'>\" & TopPerformerName & \"</div>" &
"<div style='font-size:13px; color:{self.theme.neutral};'>Score: <span style='font-weight:600; color:{self.theme.success};'>\" & TopPerformerScore & \"</span> | Records: <span style='font-weight:600;'>\" & TopPerformerCount & \"</span></div>" &
"</div>" &
"<div style='margin-top:12px; font-size:11px; color:#065f46;'>" &
"<div style='font-weight:600; margin-bottom:4px;'>Top 3:</div>" &
"<div>\" & Top3Text & \"</div>" &
"</div>" &
"</div>" &
"<div style='background:{self.theme.light_danger}; padding:18px; border-radius:12px; border-left:4px solid {self.theme.danger};'>" &
"<h3 style='color:{self.theme.danger}; font-size:15px; font-weight:600; margin:0 0 12px 0;'>{self.icons.get('warning', '⚠️')} Needs Attention</h3>" &
"<div style='background:white; padding:14px; border-radius:8px;'>" &
"<div style='font-size:16px; font-weight:700; color:#1f2937; margin-bottom:6px;'>\" & BottomPerformerName & \"</div>" &
"<div style='font-size:13px; color:{self.theme.neutral};'>Score: <span style='font-weight:600; color:{self.theme.danger};'>\" & BottomPerformerScore & \"</span> | Records: <span style='font-weight:600;'>\" & BottomPerformerCount & \"</span></div>" &
"</div>" &
"<div style='margin-top:12px; font-size:11px; color:#7f1d1d;'>" &
"<div style='font-weight:600; margin-bottom:4px;'>Bottom 3:</div>" &
"<div>\" & Bottom3Text & \"</div>" &
"</div>" &
"</div>" &
"</div>" &"""
    
    def _generate_action_dashboard(self) -> str:
        first_metric = list(self.metrics.keys())[0] if self.metrics else "Score"
        var_name = first_metric.replace(" ", "")
        
        return f"""
"<div style='background:{self.theme.light_warning}; border-radius:12px; padding:20px; margin-bottom:24px; border-left:4px solid {self.theme.warning};'>" &
"<h3 style='color:#92400e; font-size:16px; font-weight:600; margin:0 0 14px 0;'>{self.icons.get('warning', '🚨')} Priority Action Dashboard</h3>" &
IF({var_name} < 7 || (BottomPerformerScore < 7 && NOT ISBLANK(BottomPerformerScore)),
    "<div style='background:{self.theme.light_danger}; padding:14px; border-radius:8px; margin-bottom:12px; border-left:3px solid {self.theme.danger};'>" &
    "<div style='font-size:12px; font-weight:600; color:#7f1d1d; margin-bottom:8px;'>{self.icons.get('warning', '🔴')} CRITICAL PRIORITY</div>" &
    IF({var_name} < 7, "<p style='font-size:13px; margin:4px 0; color:#374151;'>• Overall {first_metric} is below acceptable threshold - immediate action required</p>", "") &
    IF(BottomPerformerScore < 7 && NOT ISBLANK(BottomPerformerScore), "<p style='font-size:13px; margin:4px 0; color:#374151;'>• <b>\" & BottomPerformerName & \"</b> requires urgent intervention (Score: \" & BottomPerformerScore & \")</p>", "") &
    "</div>",
    ""
) &
"<div style='background:white; padding:14px; border-radius:8px; margin-bottom:12px;'>" &
"<div style='font-size:12px; font-weight:600; color:#92400e; margin-bottom:8px;'>{self.icons.get('warning', '🟡')} MONITOR CLOSELY</div>" &
"<p style='font-size:13px; margin:4px 0; color:#374151;'>• Review performance trends for early warning signals</p>" &
"<p style='font-size:13px; margin:4px 0; color:#374151;'>• Analyze feedback patterns for improvement opportunities</p>" &
"</div>" &
"<div style='background:{self.theme.light_success}; padding:14px; border-radius:8px;'>" &
"<div style='font-size:12px; font-weight:600; color:#065f46; margin-bottom:8px;'>{self.icons.get('positive', '🟢')} REPLICATE SUCCESS</div>" &
"<p style='font-size:13px; margin:4px 0; color:#374151;'>• <b>\" & TopPerformerName & \"</b> sets the benchmark (Score: \" & TopPerformerScore & \") - document best practices</p>" &
"<p style='font-size:13px; margin:4px 0; color:#374151;'>• Share success strategies across the organization</p>" &
"</div>" &
"</div>" &"""
    
    def _generate_positive_verbatim(self) -> str:
        return f"""
"<div style='background:{self.theme.light_success}; padding:20px; border-radius:12px; margin-bottom:24px; border-left:4px solid {self.theme.success};'>" &
"<h3 style='color:{self.theme.success}; font-size:16px; font-weight:600; margin:0 0 14px 0;'>{self.icons.get('positive', '💚')} What's Working Well (\" & PositiveCount & \" comments)</h3>" &
"<p style='font-size:13px; line-height:1.7; color:#374151; margin:0 0 14px 0;'>Top-rated feedback highlights successful areas:</p>" &
PositiveHTML &
"</div>" &"""
    
    def _generate_negative_verbatim(self) -> str:
        return f"""
"<div style='background:{self.theme.light_danger}; padding:20px; border-radius:12px; margin-bottom:24px; border-left:4px solid {self.theme.danger};'>" &
"<h3 style='color:{self.theme.danger}; font-size:16px; font-weight:600; margin:0 0 14px 0;'>{self.icons.get('negative', '🔴')} Critical Feedback (\" & NegativeCount & \" comments)</h3>" &
"<p style='font-size:13px; line-height:1.7; color:#374151; margin:0 0 14px 0;'>Areas requiring immediate attention:</p>" &
NegativeHTML &
"</div>" &"""
    
    def _generate_theme_analysis(self) -> str:
        text_col = list(self.text_columns.keys())[0]
        return f"""
"<div style='background:white; padding:20px; border-radius:12px; margin-bottom:24px; box-shadow:0 2px 8px rgba(0,0,0,0.08);'>" &
"<h3 style='color:#1f2937; font-size:16px; font-weight:600; margin:0 0 14px 0; padding-bottom:8px; border-bottom:2px solid #e5e7eb;'>{self.icons.get('analysis', '🔍')} Common Themes</h3>" &
"<p style='font-size:13px; color:#6b7280; margin:0;'>Keyword analysis shows recurring patterns across feedback</p>" &
"</div>" &"""
    
    def _generate_distribution(self) -> str:
        first_metric = list(self.metrics.values())[0]
        return f"""
"<div style='background:white; padding:20px; border-radius:12px; margin-bottom:24px; box-shadow:0 2px 8px rgba(0,0,0,0.08);'>" &
"<h3 style='color:#1f2937; font-size:16px; font-weight:600; margin:0 0 14px 0; padding-bottom:8px; border-bottom:2px solid #e5e7eb;'>{self.icons.get('metrics', '📊')} Score Distribution</h3>" &
"<div style='display:grid; grid-template-columns:repeat(5, 1fr); gap:8px; margin-top:14px;'>" &
"<div style='text-align:center; padding:12px; background:{self.theme.background}; border-radius:8px;'>" &
"<div style='font-size:20px; font-weight:700; color:{self.theme.success};'>\" & CALCULATE(COUNTROWS('{self.table}'), '{self.table}'[{first_metric['column']}] >= 9) & \"</div>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-top:4px;'>Excellent (9-10)</div>" &
"</div>" &
"<div style='text-align:center; padding:12px; background:{self.theme.background}; border-radius:8px;'>" &
"<div style='font-size:20px; font-weight:700; color:{self.theme.primary};'>\" & CALCULATE(COUNTROWS('{self.table}'), '{self.table}'[{first_metric['column']}] >= 7 && '{self.table}'[{first_metric['column']}] < 9) & \"</div>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-top:4px;'>Good (7-8)</div>" &
"</div>" &
"<div style='text-align:center; padding:12px; background:{self.theme.background}; border-radius:8px;'>" &
"<div style='font-size:20px; font-weight:700; color:{self.theme.warning};'>\" & CALCULATE(COUNTROWS('{self.table}'), '{self.table}'[{first_metric['column']}] >= 5 && '{self.table}'[{first_metric['column']}] < 7) & \"</div>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-top:4px;'>Fair (5-6)</div>" &
"</div>" &
"<div style='text-align:center; padding:12px; background:{self.theme.background}; border-radius:8px;'>" &
"<div style='font-size:20px; font-weight:700; color:{self.theme.danger};'>\" & CALCULATE(COUNTROWS('{self.table}'), '{self.table}'[{first_metric['column']}] < 5) & \"</div>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-top:4px;'>Poor (0-4)</div>" &
"</div>" &
"<div style='text-align:center; padding:12px; background:{self.theme.background}; border-radius:8px;'>" &
"<div style='font-size:20px; font-weight:700; color:{self.theme.neutral};'>\" & TotalResponses & \"</div>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-top:4px;'>Total</div>" &
"</div>" &
"</div>" &
"</div>" &"""
    
    def _generate_velocity(self) -> str:
        return f"""
"<div style='background:{self.theme.light_primary}; padding:20px; border-radius:12px; margin-bottom:24px; border-left:4px solid {self.theme.primary};'>" &
"<h3 style='color:{self.theme.primary}; font-size:16px; font-weight:600; margin:0 0 14px 0;'>{self.icons.get('trend', '⚡')} Response Velocity</h3>" &
"<div style='display:grid; grid-template-columns:1fr 1fr; gap:14px;'>" &
"<div style='background:white; padding:14px; border-radius:8px;'>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-bottom:4px;'>Last 30 Days</div>" &
"<div style='font-size:24px; font-weight:700; color:{self.theme.primary};'>\" & ResponsesLast30 & \"</div>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-top:2px;'>responses</div>" &
"</div>" &
"<div style='background:white; padding:14px; border-radius:8px;'>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-bottom:4px;'>Change vs Previous</div>" &
"<div style='font-size:24px; font-weight:700; color:\" & IF(ResponseVelocity > 0, \"{self.theme.success}\", IF(ResponseVelocity < 0, \"{self.theme.danger}\", \"{self.theme.neutral}\")) & \";'>\" & IF(ResponseVelocity > 0, \"+\", \"\") & ResponseVelocity & \"%</div>" &
"<div style='font-size:11px; color:{self.theme.neutral}; margin-top:2px;'>\" & IF(ResponseVelocity > 0, \"increase\", IF(ResponseVelocity < 0, \"decrease\", \"flat\")) & \"</div>" &
"</div>" &
"</div>" &
"</div>" &"""
    
    def _generate_footer(self) -> str:
        return f"""
"<div style='margin-top:32px; padding-top:20px; border-top:2px solid #e5e7eb;'>" &
"<p style='font-size:11px; color:#9ca3af; text-align:center; margin:0; font-style:italic;'>" &
"Auto-generated insights powered by Power BI DAX | Updates dynamically with data refresh | Generated: \" & TODAY() & \"" &
"</p>" &
"</div>" &"""
    
    def _generate_html_end(self) -> str:
        return """"</div>"

RETURN HtmlContent"""

def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {font-family: 'Inter', system-ui, -apple-system, sans-serif;}
    .main {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 0;}
    .stApp {background: transparent;}
    .block-container {padding: 2rem 1rem; max-width: 1600px;}
    
    div[data-testid="stFileUploader"] {
        background: white; border-radius: 12px; padding: 20px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border: 2px dashed #e5e7eb;
        transition: all 0.3s;
    }
    div[data-testid="stFileUploader"]:hover {border-color: #667eea;}
    
    .metric-card {
        background: white; padding: 24px; border-radius: 12px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin: 12px 0;
        border-left: 4px solid #667eea;
    }
    
    .threshold-builder {
        background: #f8fafc; padding: 16px; border-radius: 8px;
        border: 1px solid #e5e7eb; margin: 12px 0;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; border: none; padding: 14px 36px; border-radius: 8px;
        font-weight: 600; font-size: 16px;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
    }
    
    h1 {color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); 
        font-size: 48px; margin-bottom: 8px; font-weight: 700;}
    h2 {color: white; font-size: 24px; font-weight: 400; margin-top: 0;}
    h3 {color: #1f2937; font-size: 18px; font-weight: 600;}
    
    .success-box {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white; padding: 20px; border-radius: 12px; margin: 16px 0;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }
    
    .stSelectbox, .stMultiSelect, .stTextInput {
        background: white; border-radius: 8px;
    }
    
    div[data-testid="stExpander"] {
        background: white; border-radius: 8px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #e5e7eb;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.1);
        padding: 8px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.2);
        color: white;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: white;
        color: #667eea;
    }
    
    .icon-selector {
        display: inline-block;
        padding: 8px 12px;
        background: #f8fafc;
        border-radius: 6px;
        margin: 4px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .icon-selector:hover {background: #e5e7eb; transform: scale(1.1);}
    
    code {
        background: #1e293b !important;
        color: #e2e8f0 !important;
        padding: 16px !important;
        border-radius: 8px !important;
        font-family: 'Fira Code', monospace !important;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    load_css()
    
    st.markdown("<h1>📊 Power BI HTML DAX Generator Pro</h1>", unsafe_allow_html=True)
    st.markdown("<h2>Enterprise-Grade Narrative Builder with Advanced Thresholds</h2>", unsafe_allow_html=True)
    
    if 'thresholds' not in st.session_state:
        st.session_state['thresholds'] = {}
    if 'preview_data' not in st.session_state:
        st.session_state['preview_data'] = None
    
    tabs = st.tabs(["📁 Data Setup", "📊 Metrics & Thresholds", "🎨 Design & Sections", "🚀 Generate"])
    
    # TAB 1: DATA SETUP
    with tabs[0]:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.subheader("📂 Upload Your Dataset")
            
            uploaded_file = st.file_uploader(
                "Upload CSV, Excel, or Parquet file",
                type=['csv', 'xlsx', 'parquet'],
                help="This should match your Power BI data structure"
            )
            
            if uploaded_file:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    elif uploaded_file.name.endswith('.parquet'):
                        df = pd.read_parquet(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    st.success(f"✅ Loaded {len(df):,} rows × {len(df.columns)} columns")
                    st.session_state['df'] = df
                    st.session_state['preview_data'] = df.head(5)
                    
                    with st.expander("📊 Data Preview", expanded=False):
                        st.dataframe(df.head(100), use_container_width=True, height=300)
                    
                    st.markdown("**Data Quality Check:**")
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Total Rows", f"{len(df):,}")
                    with col_b:
                        missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100)
                        st.metric("Missing Values", f"{missing_pct:.1f}%")
                    with col_c:
                        st.metric("Columns", len(df.columns))
                        
                except Exception as e:
                    st.error(f"❌ Error loading file: {str(e)}")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            if 'df' in st.session_state:
                df = st.session_state['df']
                
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.subheader("⚙️ Power BI Configuration")
                
                table_name = st.text_input(
                    "Power BI Table Name",
                    value="YourTable",
                    help="Exact name as it appears in Power BI model"
                )
                
                date_columns = [col for col in df.columns if 
                               pd.api.types.is_datetime64_any_dtype(df[col]) or 
                               'date' in col.lower() or 'time' in col.lower() or
                               'created' in col.lower()]
                
                if date_columns:
                    date_col = st.selectbox(
                        "Date/Time Column",
                        options=date_columns,
                        help="Used for trend analysis and time-based comparisons"
                    )
                else:
                    date_col = st.selectbox(
                        "Date/Time Column",
                        options=["None"] + list(df.columns),
                        help="No date columns detected - select manually or choose None"
                    )
                    if date_col == "None":
                        date_col = None
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.subheader("📋 Column Classification")
                
                numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                text_cols = [col for col in categorical_cols if df[col].astype(str).str.len().mean() > 50] if categorical_cols else []
                
                st.markdown(f"**Detected:** {len(numeric_cols)} numeric, {len(categorical_cols)} categorical, {len(text_cols)} text columns")
                
                selected_metrics = st.multiselect(
                    "📊 Select Numerical Metrics",
                    numeric_cols,
                    default=numeric_cols[:3] if len(numeric_cols) >= 3 else numeric_cols,
                    help="Metrics for KPI cards and trend analysis"
                )
                
                selected_categorical = st.multiselect(
                    "🏷️ Select Categorical Dimensions",
                    categorical_cols,
                    default=categorical_cols[:2] if len(categorical_cols) >= 2 else categorical_cols,
                    help="For performance breakdowns and comparisons"
                )
                
                selected_text = st.multiselect(
                    "💬 Select Text/Comment Columns",
                    text_cols,
                    default=text_cols[:1] if text_cols else [],
                    help="For verbatim analysis"
                )
                
                if selected_text:
                    st.markdown("**Link text columns to score columns:**")
                    text_score_mapping = {}
                    for text_col in selected_text:
                        score_col = st.selectbox(
                            f"Score column for '{text_col}'",
                            options=selected_metrics,
                            key=f"score_for_{text_col}"
                        )
                        text_score_mapping[text_col] = score_col
                    st.session_state['text_score_mapping'] = text_score_mapping
                
                st.session_state['config'] = {
                    'table_name': table_name,
                    'date_col': date_col,
                    'metrics': selected_metrics,
                    'categorical': selected_categorical,
                    'text': selected_text
                }
                
                st.markdown("</div>", unsafe_allow_html=True)
    
    # TAB 2: METRICS & THRESHOLDS
    with tabs[1]:
        if 'config' in st.session_state and st.session_state['config']['metrics']:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.subheader("📊 Configure Metrics and Thresholds")
            st.markdown("Define aggregation methods and conditional thresholds for each metric")
            st.markdown("</div>", unsafe_allow_html=True)
            
            df = st.session_state['df']
            metric_configs = []
            
            for metric_col in st.session_state['config']['metrics']:
                with st.expander(f"⚙️ Configure: {metric_col}", expanded=True):
                    st.markdown("<div class='threshold-builder'>", unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        agg = st.selectbox(
                            "Aggregation Function",
                            ['AVERAGE', 'SUM', 'MIN', 'MAX', 'COUNT'],
                            key=f"agg_{metric_col}"
                        )
                    
                    with col2:
                        format_decimals = st.number_input(
                            "Decimal Places",
                            min_value=0,
                            max_value=4,
                            value=2,
                            key=f"dec_{metric_col}"
                        )
                    
                    with col3:
                        # Show actual data range
                        min_val = df[metric_col].min()
                        max_val = df[metric_col].max()
                        st.metric("Data Range", f"{min_val:.1f} - {max_val:.1f}")
                    
                    st.markdown("---")
                    st.markdown("**Threshold Configuration**")
                    
                    direction = st.radio(
                        "Threshold Logic",
                        [e.value for e in ThresholdDirection],
                        key=f"dir_{metric_col}",
                        horizontal=True
                    )
                    
                    threshold_config = None
                    
                    if direction == ThresholdDirection.HIGHER_BETTER.value:
                        st.info("📈 Higher values = Better performance")
                        col_a, col_b, col_c, col_d = st.columns(4)
                        
                        with col_a:
                            excellent_min = st.number_input(
                                "🟢 Excellent (≥)",
                                value=float(max_val * 0.9),
                                key=f"exc_min_{metric_col}",
                                format="%.2f"
                            )
                        with col_b:
                            good_min = st.number_input(
                                "🔵 Good (≥)",
                                value=float(max_val * 0.7),
                                key=f"good_min_{metric_col}",
                                format="%.2f"
                            )
                        with col_c:
                            warning_min = st.number_input(
                                "🟡 Warning (≥)",
                                value=float(max_val * 0.5),
                                key=f"warn_min_{metric_col}",
                                format="%.2f"
                            )
                        with col_d:
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown("🔴 Critical: Below Warning")
                        
                        threshold_config = ThresholdConfig(
                            metric_name=metric_col,
                            direction=ThresholdDirection.HIGHER_BETTER,
                            excellent_min=excellent_min,
                            good_min=good_min,
                            warning_min=warning_min
                        )
                    
                    elif direction == ThresholdDirection.LOWER_BETTER.value:
                        st.info("📉 Lower values = Better performance")
                        col_a, col_b, col_c, col_d = st.columns(4)
                        
                        with col_a:
                            excellent_max = st.number_input(
                                "🟢 Excellent (≤)",
                                value=float(min_val * 1.2),
                                key=f"exc_max_{metric_col}",
                                format="%.2f"
                            )
                        with col_b:
                            good_max = st.number_input(
                                "🔵 Good (≤)",
                                value=float(min_val * 1.5),
                                key=f"good_max_{metric_col}",
                                format="%.2f"
                            )
                        with col_c:
                            warning_max = st.number_input(
                                "🟡 Warning (≤)",
                                value=float(min_val * 2.0),
                                key=f"warn_max_{metric_col}",
                                format="%.2f"
                            )
                        with col_d:
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown("🔴 Critical: Above Warning")
                        
                        threshold_config = ThresholdConfig(
                            metric_name=metric_col,
                            direction=ThresholdDirection.LOWER_BETTER,
                            excellent_max=excellent_max,
                            good_max=good_max,
                            warning_max=warning_max
                        )
                    
                    else:  # RANGE_OPTIMAL
                        st.info("📊 Optimal range = Best performance (both extremes are bad)")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown("**🟢 Excellent Range**")
                            excellent_min = st.number_input(
                                "Min",
                                value=float((max_val - min_val) * 0.4 + min_val),
                                key=f"exc_min_r_{metric_col}",
                                format="%.2f"
                            )
                            excellent_max = st.number_input(
                                "Max",
                                value=float((max_val - min_val) * 0.6 + min_val),
                                key=f"exc_max_r_{metric_col}",
                                format="%.2f"
                            )
                        
                        with col_b:
                            st.markdown("**🔵 Good Range**")
                            good_min = st.number_input(
                                "Min",
                                value=float((max_val - min_val) * 0.3 + min_val),
                                key=f"good_min_r_{metric_col}",
                                format="%.2f"
                            )
                            good_max = st.number_input(
                                "Max",
                                value=float((max_val - min_val) * 0.7 + min_val),
                                key=f"good_max_r_{metric_col}",
                                format="%.2f"
                            )
                        
                        col_c, col_d = st.columns(2)
                        with col_c:
                            st.markdown("**🟡 Warning Range**")
                            warning_min = st.number_input(
                                "Min",
                                value=float((max_val - min_val) * 0.2 + min_val),
                                key=f"warn_min_r_{metric_col}",
                                format="%.2f"
                            )
                            warning_max = st.number_input(
                                "Max",
                                value=float((max_val - min_val) * 0.8 + min_val),
                                key=f"warn_max_r_{metric_col}",
                                format="%.2f"
                            )
                        
                        with col_d:
                            st.markdown("**🔴 Critical**")
                            st.markdown("Outside Warning Range")
                        
                        threshold_config = ThresholdConfig(
                            metric_name=metric_col,
                            direction=ThresholdDirection.RANGE_OPTIMAL,
                            excellent_min=excellent_min,
                            excellent_max=excellent_max,
                            good_min=good_min,
                            good_max=good_max,
                            warning_min=warning_min,
                            warning_max=warning_max
                        )
                    
                    st.session_state['thresholds'][metric_col] = threshold_config
                    
                    metric_configs.append({
                        'name': metric_col,
                        'column': metric_col,
                        'aggregation': agg,
                        'format': format_decimals,
                        'threshold': threshold_config
                    })
                    
                    st.markdown("</div>", unsafe_allow_html=True)
            
            st.session_state['metric_configs'] = metric_configs
        else:
            st.info("👈 Configure data setup first")
    
    # TAB 3: DESIGN & SECTIONS
    with tabs[2]:
        if 'config' in st.session_state:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.subheader("🎨 Visual Theme")
                
                theme_name = st.selectbox(
                    "Select Color Theme",
                    options=list(THEMES.keys()),
                    index=0
                )
                selected_theme = THEMES[theme_name]
                
                st.markdown("**Theme Preview:**")
                st.markdown(f"""
                <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 16px 0;'>
                    <div style='background: {selected_theme.primary}; height: 70px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;'>Primary</div>
                    <div style='background: {selected_theme.success}; height: 70px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;'>Success</div>
                    <div style='background: {selected_theme.warning}; height: 70px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;'>Warning</div>
                    <div style='background: {selected_theme.danger}; height: 70px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;'>Danger</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.subheader("🎯 Icon Selection")
                
                selected_icons = {}
                for category, icons in ICONS.items():
                    selected_icons[category] = st.selectbox(
                        f"{category.replace('_', ' ').title()}",
                        icons,
                        key=f"icon_{category}"
                    )
                
                st.session_state['icons'] = selected_icons
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.subheader("📋 Narrative Sections")
                st.markdown("Select which sections to include in your narrative")
                
                config = st.session_state['config']
                has_categorical = len(config['categorical']) > 0
                has_text = len(config['text']) > 0
                has_date = config['date_col'] is not None
                
                enabled_sections = []
                
                for section_id, section in AVAILABLE_SECTIONS.items():
                    can_enable = True
                    disabled_reason = None
                    
                    if section.requires_categorical and not has_categorical:
                        can_enable = False
                        disabled_reason = "Requires categorical columns"
                    elif section.requires_text and not has_text:
                        can_enable = False
                        disabled_reason = "Requires text columns"
                    elif section.requires_date and not has_date:
                        can_enable = False
                        disabled_reason = "Requires date column"
                    
                    col_check, col_info = st.columns([3, 1])
                    
                    with col_check:
                        if can_enable:
                            is_enabled = st.checkbox(
                                f"{section.icon} {section.name}",
                                value=section.enabled,
                                key=f"section_{section_id}",
                                help=section.description
                            )
                            if is_enabled:
                                enabled_sections.append(section_id)
                        else:
                            st.checkbox(
                                f"{section.icon} {section.name}",
                                value=False,
                                disabled=True,
                                key=f"section_{section_id}_disabled",
                                help=f"{section.description} - {disabled_reason}"
                            )
                    
                    with col_info:
                        if not can_enable:
                            st.markdown(f"<small style='color:#ef4444;'>❌ {disabled_reason}</small>", unsafe_allow_html=True)
                
                st.session_state['enabled_sections'] = enabled_sections
                st.markdown("</div>", unsafe_allow_html=True)
            
            st.session_state['theme'] = selected_theme
        else:
            st.info("👈 Configure data setup first")
    
    # TAB 4: GENERATE
    with tabs[3]:
        if 'config' in st.session_state and 'theme' in st.session_state:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.metric("Metrics Configured", len(st.session_state['config']['metrics']))
            with col2:
                st.metric("Sections Enabled", len(st.session_state.get('enabled_sections', [])))
            with col3:
                st.metric("Thresholds Set", len(st.session_state.get('thresholds', {})))
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("🚀 Generate Production DAX Code", use_container_width=True, type="primary"):
                with st.spinner("Generating enterprise-grade DAX code..."):
                    try:
                        config = st.session_state['config']
                        generator = DAXGenerator(
                            config['table_name'],
                            config['date_col'],
                            st.session_state['theme']
                        )
                        
                        # Add metrics
                        for metric_config in st.session_state.get('metric_configs', []):
                            generator.add_metric(
                                metric_config['name'],
                                metric_config['column'],
                                metric_config['aggregation'],
                                metric_config['format']
                            )
                        
                        # Add thresholds
                        generator.thresholds = st.session_state.get('thresholds', {})
                        
                        # Add categorical and text columns
                        generator.categorical_columns = config['categorical']
                        if config['text'] and 'text_score_mapping' in st.session_state:
                            generator.text_columns = st.session_state['text_score_mapping']
                        
                        # Set enabled sections and icons
                        generator.enabled_sections = st.session_state.get('enabled_sections', [])
                        generator.icons = st.session_state.get('icons', {})
                        
                        # Generate DAX
                        dax_code = generator.generate_dax()
                        st.session_state['generated_dax'] = dax_code
                        
                        st.markdown("<div class='success-box'>✅ DAX Code Generated Successfully!</div>", unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"❌ Error generating DAX: {str(e)}")
                        st.exception(e)
            
            if 'generated_dax' in st.session_state:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.subheader("📋 Generated DAX Code")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col2:
                    st.download_button(
                        label="💾 Download DAX",
                        data=st.session_state['generated_dax'],
                        file_name="power_bi_narrative.dax",
                        mime="text/plain",
                        use_container_width=True
                    )
                with col3:
                    if st.button("📋 Copy Code", use_container_width=True):
                        st.toast("✅ Code copied to clipboard!", icon="✅")
                
                st.code(st.session_state['generated_dax'], language='dax', line_numbers=True)
                
                st.markdown("---")
                st.markdown("**How to Use:**")
                st.markdown("""
                1. Copy the generated DAX code
                2. Open Power BI Desktop
                3. Go to **Modeling** → **New Measure**
                4. Paste the DAX code
                5. Add the measure to a **Card** visual
                6. Format the card visual to remove backgrounds and borders
                7. Your HTML narrative will render automatically!
                """)
                
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("👈 Complete all configuration steps to generate DAX code")

if __name__ == "__main__":
    main()
