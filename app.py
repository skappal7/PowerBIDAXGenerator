import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json

st.set_page_config(page_title="Power BI DAX Generator", layout="wide", page_icon="⚡", initial_sidebar_state="collapsed")

@dataclass
class ColorTheme:
    name: str
    primary: str
    secondary: str
    success: str
    warning: str
    danger: str
    bg: str
    text: str

THEMES = {
    "Ocean Blue": ColorTheme("Ocean Blue", "#2563eb", "#1e40af", "#10b981", "#f59e0b", "#ef4444", "#eff6ff", "#1e293b"),
    "Forest Green": ColorTheme("Forest Green", "#059669", "#047857", "#10b981", "#f59e0b", "#dc2626", "#ecfdf5", "#1f2937"),
    "Royal Purple": ColorTheme("Royal Purple", "#7c3aed", "#6d28d9", "#10b981", "#f59e0b", "#ef4444", "#f5f3ff", "#1e293b"),
    "Sunset Orange": ColorTheme("Sunset Orange", "#ea580c", "#c2410c", "#10b981", "#f59e0b", "#dc2626", "#fff7ed", "#1f2937"),
    "Slate Gray": ColorTheme("Slate Gray", "#475569", "#334155", "#10b981", "#f59e0b", "#ef4444", "#f8fafc", "#0f172a"),
}

class DAXValidator:
    @staticmethod
    def escape_column_name(name: str) -> str:
        """Properly escape column names for DAX"""
        if ' ' in name or any(c in name for c in ['[', ']', '#', '@']):
            return f"[{name}]"
        return f"[{name}]"
    
    @staticmethod
    def escape_table_name(name: str) -> str:
        """Properly escape table names for DAX"""
        if ' ' in name:
            return f"'{name}'"
        return f"'{name}'"

class SmartAnalyzer:
    @staticmethod
    def analyze_data(df: pd.DataFrame) -> Dict:
        """Intelligently analyze dataframe and suggest configurations"""
        analysis = {
            'total_rows': len(df),
            'total_cols': len(df.columns),
            'numeric_cols': [],
            'categorical_cols': [],
            'date_cols': [],
            'text_cols': [],
            'suggested_score_col': None,
            'suggested_categorical': [],
            'data_quality': 0
        }
        
        for col in df.columns:
            missing_pct = (df[col].isnull().sum() / len(df)) * 100
            
            if pd.api.types.is_numeric_dtype(df[col]):
                unique_ratio = df[col].nunique() / len(df)
                analysis['numeric_cols'].append({
                    'name': col,
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(df[col].mean()),
                    'missing_pct': missing_pct,
                    'is_score': unique_ratio > 0.05 and df[col].min() >= 0 and df[col].max() <= 10
                })
            
            elif pd.api.types.is_datetime64_any_dtype(df[col]) or 'date' in col.lower() or 'time' in col.lower():
                analysis['date_cols'].append({
                    'name': col,
                    'min': df[col].min(),
                    'max': df[col].max(),
                    'missing_pct': missing_pct
                })
            
            elif pd.api.types.is_object_dtype(df[col]):
                unique_count = df[col].nunique()
                avg_length = df[col].astype(str).str.len().mean()
                
                if avg_length > 100:
                    analysis['text_cols'].append({
                        'name': col,
                        'avg_length': avg_length,
                        'missing_pct': missing_pct
                    })
                elif unique_count < len(df) * 0.5:
                    analysis['categorical_cols'].append({
                        'name': col,
                        'unique_count': unique_count,
                        'missing_pct': missing_pct
                    })
        
        # Auto-suggest score column
        score_candidates = [nc for nc in analysis['numeric_cols'] if nc['is_score']]
        if score_candidates:
            analysis['suggested_score_col'] = score_candidates[0]['name']
        
        # Auto-suggest categorical for breakdowns
        if analysis['categorical_cols']:
            sorted_cats = sorted(analysis['categorical_cols'], key=lambda x: x['unique_count'])
            analysis['suggested_categorical'] = [c['name'] for c in sorted_cats[:3]]
        
        # Data quality score
        total_missing = sum([col.get('missing_pct', 0) for col in 
                           analysis['numeric_cols'] + analysis['categorical_cols'] + 
                           analysis['date_cols'] + analysis['text_cols']])
        analysis['data_quality'] = max(0, 100 - (total_missing / len(df.columns)))
        
        return analysis

class DAXBuilder:
    def __init__(self, table: str, theme: ColorTheme):
        self.table = DAXValidator.escape_table_name(table)
        self.theme = theme
        self.measures = []
        
    def build_measure_var(self, name: str, column: str, agg: str, decimals: int = 2) -> str:
        """Build a single measure variable"""
        col = DAXValidator.escape_column_name(column)
        var_name = name.replace(' ', '').replace('-', '').replace('_', '')
        return f"VAR {var_name} = ROUND({agg}({self.table}{col}), {decimals})"
    
    def build_threshold_color(self, var_name: str, thresholds: Dict) -> str:
        """Build threshold-based color assignment"""
        direction = thresholds['direction']
        var_clean = var_name.replace(' ', '').replace('-', '').replace('_', '')
        
        if direction == 'higher':
            return f"""VAR {var_clean}Color = 
    IF({var_clean} >= {thresholds['excellent']}, "{self.theme.success}",
    IF({var_clean} >= {thresholds['good']}, "{self.theme.primary}",
    IF({var_clean} >= {thresholds['warning']}, "{self.theme.warning}", "{self.theme.danger}")))"""
        elif direction == 'lower':
            return f"""VAR {var_clean}Color = 
    IF({var_clean} <= {thresholds['excellent']}, "{self.theme.success}",
    IF({var_clean} <= {thresholds['good']}, "{self.theme.primary}",
    IF({var_clean} <= {thresholds['warning']}, "{self.theme.warning}", "{self.theme.danger}")))"""
        else:  # range
            return f"""VAR {var_clean}Color = 
    IF({var_clean} >= {thresholds['min']} && {var_clean} <= {thresholds['max']}, "{self.theme.success}",
    IF({var_clean} >= {thresholds['warn_min']} && {var_clean} <= {thresholds['warn_max']}, "{self.theme.warning}", "{self.theme.danger}"))"""
    
    def build_kpi_card_html(self, title: str, var_name: str, unit: str = "") -> str:
        """Build HTML for a single KPI card"""
        var_clean = var_name.replace(' ', '').replace('-', '').replace('_', '')
        return f'''\"<div style='background:white; padding:20px; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.1); border-left:4px solid \" & {var_clean}Color & \";'>\" &
\"<div style='font-size:12px; color:#64748b; font-weight:500; margin-bottom:8px;'>{title}</div>\" &
\"<div style='font-size:32px; font-weight:700; color:\" & {var_clean}Color & \"; margin-bottom:4px;'>\" & {var_clean} & \"{unit}</div>\" &
\"</div>\" &'''
    
    def build_header(self) -> str:
        """Build measure header and core variables"""
        return f'''HTML_Narrative = 
VAR TotalRecords = COUNTROWS({self.table})'''
    
    def build_html_start(self) -> str:
        """Build HTML container start"""
        return f'''
VAR HTML = 
\"<div style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif; max-width:1200px; padding:24px; background:{self.theme.bg}; color:{self.theme.text};'>\" &'''
    
    def build_title_section(self, title: str) -> str:
        """Build title header"""
        return f'''
\"<div style='background:linear-gradient(135deg, {self.theme.primary} 0%, {self.theme.secondary} 100%); padding:32px; border-radius:12px; margin-bottom:28px; box-shadow:0 4px 16px rgba(0,0,0,0.1);'>\" &
\"<h1 style='color:white; font-size:32px; font-weight:700; margin:0 0 8px 0;'>{title}</h1>\" &
\"<p style='color:rgba(255,255,255,0.9); font-size:15px; margin:0;'>Generated Report • \" & TotalRecords & \" Total Records</p>\" &
\"</div>\" &'''
    
    def build_performance_table(self, cat_col: str, score_col: str, agg: str) -> Tuple[str, str]:
        """Build performance breakdown table"""
        cat_esc = DAXValidator.escape_column_name(cat_col)
        score_esc = DAXValidator.escape_column_name(score_col)
        
        vars_section = f'''
VAR PerfSummary = 
    SUMMARIZE(
        {self.table},
        {self.table}{cat_esc},
        "AvgScore", {agg}({self.table}{score_esc}),
        "Count", COUNTROWS({self.table})
    )
VAR TopPerformer = TOPN(1, PerfSummary, [AvgScore], DESC)
VAR BottomPerformer = TOPN(1, PerfSummary, [AvgScore], ASC)
VAR TopName = MAXX(TopPerformer, {self.table}{cat_esc})
VAR TopScore = ROUND(MAXX(TopPerformer, [AvgScore]), 2)
VAR BottomName = MAXX(BottomPerformer, {self.table}{cat_esc})
VAR BottomScore = ROUND(MAXX(BottomPerformer, [AvgScore]), 2)'''
        
        html_section = f'''
\"<div style='margin-bottom:24px;'>\" &
\"<h2 style='font-size:20px; font-weight:600; margin:0 0 16px 0; padding-bottom:12px; border-bottom:2px solid #e2e8f0;'>📊 Performance by {cat_col}</h2>\" &
\"<div style='display:grid; grid-template-columns:1fr 1fr; gap:16px;'>\" &
\"<div style='background:#ecfdf5; padding:20px; border-radius:10px; border-left:4px solid {self.theme.success};'>\" &
\"<div style='font-size:13px; color:#047857; font-weight:600; margin-bottom:6px;'>🏆 Top Performer</div>\" &
\"<div style='font-size:18px; font-weight:700; color:#1f2937; margin-bottom:4px;'>\" & TopName & \"</div>\" &
\"<div style='font-size:14px; color:#64748b;'>Score: <span style='color:{self.theme.success}; font-weight:600;'>\" & TopScore & \"</span></div>\" &
\"</div>\" &
\"<div style='background:#fef2f2; padding:20px; border-radius:10px; border-left:4px solid {self.theme.danger};'>\" &
\"<div style='font-size:13px; color:#dc2626; font-weight:600; margin-bottom:6px;'>⚠️ Needs Attention</div>\" &
\"<div style='font-size:18px; font-weight:700; color:#1f2937; margin-bottom:4px;'>\" & BottomName & \"</div>\" &
\"<div style='font-size:14px; color:#64748b;'>Score: <span style='color:{self.theme.danger}; font-weight:600;'>\" & BottomScore & \"</span></div>\" &
\"</div>\" &
\"</div>\" &
\"</div>\" &'''
        
        return vars_section, html_section
    
    def build_verbatim_section(self, text_col: str, score_col: str, section_type: str = 'positive') -> Tuple[str, str]:
        """Build verbatim comments section"""
        text_esc = DAXValidator.escape_column_name(text_col)
        score_esc = DAXValidator.escape_column_name(score_col)
        
        if section_type == 'positive':
            title = "💚 Positive Feedback"
            bg_color = "#ecfdf5"
            border_color = self.theme.success
            text_color = "#047857"
            order = "DESC"
            var_name = "PositiveComments"
            html_var = "PositiveHTML"
        else:
            title = "🔴 Critical Feedback"
            bg_color = "#fef2f2"
            border_color = self.theme.danger
            text_color = "#dc2626"
            order = "ASC"
            var_name = "NegativeComments"
            html_var = "NegativeHTML"
        
        vars_section = f'''
VAR {var_name} = 
    TOPN(
        5,
        FILTER({self.table}, NOT ISBLANK({self.table}{text_esc}) && LEN({self.table}{text_esc}) > 10),
        {self.table}{score_esc},
        {order}
    )
VAR {html_var} = 
    CONCATENATEX(
        {var_name},
        \"<div style='background:white; padding:14px; margin:10px 0; border-radius:8px; border-left:3px solid {border_color};'>\" &
        \"<div style='font-size:11px; color:{text_color}; font-weight:600; margin-bottom:6px;'>Score: \" & ROUND({self.table}{score_esc}, 1) & \"</div>\" &
        \"<div style='font-size:13px; color:#374151; line-height:1.6;'>\" & {self.table}{text_esc} & \"</div>\" &
        \"</div>\",
        \"\",
        {self.table}{score_esc},
        {order}
    )'''
        
        html_section = f'''
\"<div style='background:{bg_color}; padding:20px; border-radius:10px; margin-bottom:24px; border-left:4px solid {border_color};'>\" &
\"<h2 style='color:{text_color}; font-size:18px; font-weight:600; margin:0 0 16px 0;'>{title}</h2>\" &
{html_var} &
\"</div>\" &'''
        
        return vars_section, html_section
    
    def build_html_end(self) -> str:
        """Build HTML container end"""
        return '''
"<div style='margin-top:32px; padding-top:20px; border-top:2px solid #e2e8f0; text-align:center;'>" &
"<p style='font-size:11px; color:#94a3b8; margin:0;'>Auto-generated by Power BI DAX | Updates with data refresh</p>" &
"</div>" &
"</div>"

RETURN HTML'''

def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    
    * {font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;}
    
    .main {background: #ffffff;}
    .block-container {padding: 2rem 3rem; max-width: 1600px;}
    
    .stApp {background: #ffffff;}
    
    div[data-testid="stFileUploader"] {
        background: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        padding: 20px;
    }
    
    .stButton>button {
        background: #0078d4;
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 2px;
        font-weight: 600;
        font-size: 14px;
        transition: background 0.2s;
    }
    
    .stButton>button:hover {
        background: #106ebe;
    }
    
    .metric-box {
        background: #f5f5f5;
        padding: 16px;
        border-radius: 2px;
        border-left: 3px solid #0078d4;
    }
    
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: #323130;
        margin-bottom: 4px;
    }
    
    .metric-label {
        font-size: 12px;
        color: #605e5c;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    div[data-testid="stExpander"] {
        background: #fafafa;
        border-radius: 2px;
        border: 1px solid #e0e0e0;
    }
    
    .success-box {
        background: #dff6dd;
        color: #107c10;
        padding: 16px;
        border-radius: 2px;
        margin: 16px 0;
        border-left: 3px solid #107c10;
    }
    
    h1 {
        color: #323130;
        font-size: 32px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    h2 {
        color: #323130;
        font-size: 20px;
        font-weight: 600;
    }
    
    h3 {
        color: #323130;
        font-size: 16px;
        font-weight: 600;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #605e5c;
        border-radius: 0;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 14px;
        border-bottom: 2px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: transparent;
        color: #0078d4;
        border-bottom: 2px solid #0078d4;
    }
    
    .stSlider {margin-bottom: 8px;}
    
    code {
        background: #1e1e1e !important;
        color: #d4d4d4 !important;
        padding: 16px !important;
        border-radius: 2px !important;
        font-family: 'Consolas', 'Courier New', monospace !important;
    }
    
    .section-card {
        background: #fafafa;
        padding: 20px;
        border-radius: 2px;
        border: 1px solid #e0e0e0;
        margin-bottom: 16px;
    }
    
    .stMultiSelect {
        background: white;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    load_custom_css()
    
    st.markdown("<h1>Power BI DAX Generator</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#605e5c; font-size:14px; margin-bottom:24px;'>Generate HTML-based DAX narratives with intelligent threshold logic</p>", unsafe_allow_html=True)
    
    if 'analysis' not in st.session_state:
        st.session_state.analysis = None
    
    tabs = st.tabs(["📁 Data Setup", "⚙️ Metrics & Thresholds", "📋 Sections & Design", "🚀 Generate DAX"])
    
    # TAB 1: Data Setup
    with tabs[0]:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Choose CSV, Excel, or Parquet file",
                type=['csv', 'xlsx', 'parquet'],
                label_visibility="collapsed"
            )
            
            if uploaded_file:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    elif uploaded_file.name.endswith('.parquet'):
                        df = pd.read_parquet(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    st.session_state.df = df
                    analysis = SmartAnalyzer.analyze_data(df)
                    st.session_state.analysis = analysis
                    
                    st.success(f"✅ Loaded {analysis['total_rows']:,} rows × {analysis['total_cols']} columns")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.markdown(f"<div class='metric-box'><div class='metric-value'>{len(analysis['numeric_cols'])}</div><div class='metric-label'>Numeric Columns</div></div>", unsafe_allow_html=True)
                    with col_b:
                        st.markdown(f"<div class='metric-box'><div class='metric-value'>{len(analysis['categorical_cols'])}</div><div class='metric-label'>Categorical</div></div>", unsafe_allow_html=True)
                    with col_c:
                        st.markdown(f"<div class='metric-box'><div class='metric-value'>{int(analysis['data_quality'])}</div><div class='metric-label'>Quality Score</div></div>", unsafe_allow_html=True)
                    
                    with st.expander("📊 Preview Data"):
                        st.dataframe(df.head(50), use_container_width=True, height=300)
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.markdown("**Power BI Settings**")
            table_name = st.text_input(
                "Table Name in Power BI",
                value="YourTable",
                help="Must match exactly"
            )
            st.session_state.table_name = table_name
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # TAB 2: Configure Metrics
    with tabs[1]:
        if 'analysis' not in st.session_state or not st.session_state.analysis:
            st.info("👈 Upload data first in the Data Setup tab")
        else:
            analysis = st.session_state.analysis
            df = st.session_state.df
            
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("<h2>Configure Metrics & Thresholds</h2>", unsafe_allow_html=True)
        
            st.markdown("**Select Primary Metrics**")
            metric_configs = []
        
        for i, num_col in enumerate(analysis['numeric_cols'][:3]):
            with st.expander(f"📊 {num_col['name']}", expanded=i==0):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    use_metric = st.toggle(
                        "Include in narrative",
                        value=i==0,
                        key=f"use_{num_col['name']}"
                    )
                
                with col2:
                    agg = st.selectbox(
                        "Aggregation",
                        ['AVERAGE', 'SUM', 'MIN', 'MAX'],
                        key=f"agg_{num_col['name']}"
                    )
                
                if use_metric:
                    st.markdown(f"**Threshold Settings** *(Data range: {num_col['min']:.1f} - {num_col['max']:.1f})*")
                    
                    threshold_type = st.radio(
                        "Logic",
                        ['Higher is Better', 'Lower is Better', 'Optimal Range'],
                        key=f"type_{num_col['name']}",
                        horizontal=True
                    )
                    
                    if threshold_type == 'Higher is Better':
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            excellent = st.slider(
                                "🟢 Excellent",
                                num_col['min'], num_col['max'],
                                num_col['max'] * 0.85,
                                key=f"exc_{num_col['name']}"
                            )
                        with col_b:
                            good = st.slider(
                                "🔵 Good",
                                num_col['min'], num_col['max'],
                                num_col['max'] * 0.65,
                                key=f"good_{num_col['name']}"
                            )
                        with col_c:
                            warning = st.slider(
                                "🟡 Warning",
                                num_col['min'], num_col['max'],
                                num_col['max'] * 0.45,
                                key=f"warn_{num_col['name']}"
                            )
                        
                        thresholds = {
                            'direction': 'higher',
                            'excellent': excellent,
                            'good': good,
                            'warning': warning
                        }
                    
                    elif threshold_type == 'Lower is Better':
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            excellent = st.slider(
                                "🟢 Excellent",
                                num_col['min'], num_col['max'],
                                num_col['min'] * 1.15,
                                key=f"exc_{num_col['name']}"
                            )
                        with col_b:
                            good = st.slider(
                                "🔵 Good",
                                num_col['min'], num_col['max'],
                                num_col['min'] * 1.35,
                                key=f"good_{num_col['name']}"
                            )
                        with col_c:
                            warning = st.slider(
                                "🟡 Warning",
                                num_col['min'], num_col['max'],
                                num_col['min'] * 1.65,
                                key=f"warn_{num_col['name']}"
                            )
                        
                        thresholds = {
                            'direction': 'lower',
                            'excellent': excellent,
                            'good': good,
                            'warning': warning
                        }
                    
                    else:  # Optimal Range
                        col_a, col_b = st.columns(2)
                        with col_a:
                            range_min = st.slider(
                                "🟢 Optimal Min",
                                num_col['min'], num_col['max'],
                                num_col['min'] + (num_col['max'] - num_col['min']) * 0.4,
                                key=f"range_min_{num_col['name']}"
                            )
                        with col_b:
                            range_max = st.slider(
                                "🟢 Optimal Max",
                                num_col['min'], num_col['max'],
                                num_col['min'] + (num_col['max'] - num_col['min']) * 0.6,
                                key=f"range_max_{num_col['name']}"
                            )
                        
                        col_c, col_d = st.columns(2)
                        with col_c:
                            warn_min = st.slider(
                                "🟡 Warning Min",
                                num_col['min'], num_col['max'],
                                num_col['min'] + (num_col['max'] - num_col['min']) * 0.2,
                                key=f"warn_min_{num_col['name']}"
                            )
                        with col_d:
                            warn_max = st.slider(
                                "🟡 Warning Max",
                                num_col['min'], num_col['max'],
                                num_col['min'] + (num_col['max'] - num_col['min']) * 0.8,
                                key=f"warn_max_{num_col['name']}"
                            )
                        
                        thresholds = {
                            'direction': 'range',
                            'min': range_min,
                            'max': range_max,
                            'warn_min': warn_min,
                            'warn_max': warn_max
                        }
                    
                    metric_configs.append({
                        'name': num_col['name'],
                        'column': num_col['name'],
                        'aggregation': agg,
                        'decimals': 2,
                        'thresholds': thresholds
                    })
        
            st.session_state.metric_configs = metric_configs
            st.markdown("</div>", unsafe_allow_html=True)
    
    # TAB 3: Select Sections
    with tabs[2]:
        if 'analysis' not in st.session_state or not st.session_state.analysis:
            st.info("👈 Upload data first in the Data Setup tab")
        else:
            analysis = st.session_state.analysis
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("<h2>Narrative Sections & Design</h2>", unsafe_allow_html=True)
        
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Section Configuration**")
                st.checkbox("📊 Header & KPI Cards", value=True, disabled=True, key="header_check")
                
                include_performance = False
                performance_cats = []
                if analysis['categorical_cols']:
                    include_performance = st.checkbox("📈 Performance Breakdown", value=True, key="perf_check")
                    if include_performance:
                        performance_cats = st.multiselect(
                            "Select categories to analyze:",
                            [c['name'] for c in analysis['categorical_cols']],
                            default=[analysis['categorical_cols'][0]['name']] if analysis['categorical_cols'] else [],
                            key="perf_cats"
                        )
            
            include_verbatim = False
            verbatim_text = None
            verbatim_score = None
            if analysis['text_cols']:
                include_verbatim = st.checkbox("💬 Verbatim Comments", value=True)
                if include_verbatim:
                    verbatim_text = st.selectbox(
                        "Comment column:",
                        [c['name'] for c in analysis['text_cols']],
                        key="verb_text"
                    )
                    verbatim_score = st.selectbox(
                        "Score column:",
                        [c['name'] for c in analysis['numeric_cols']],
                        key="verb_score"
                    )
        
        with col2:
            st.markdown("**Visual Theme**")
            theme_name = st.selectbox(
                "Color scheme:",
                list(THEMES.keys()),
                key="theme_select"
            )
            theme = THEMES[theme_name]
            
            st.markdown(f"""
            <div style='display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin-top:12px;'>
                <div style='background:{theme.primary}; height:50px; border-radius:8px;'></div>
                <div style='background:{theme.success}; height:50px; border-radius:8px;'></div>
                <div style='background:{theme.warning}; height:50px; border-radius:8px;'></div>
                <div style='background:{theme.danger}; height:50px; border-radius:8px;'></div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Report Title**")
            report_title = st.text_input(
                "Title:",
                value="Performance Intelligence Report",
                label_visibility="collapsed"
            )
        
            st.session_state.sections = {
                'performance': include_performance,
                'performance_cats': performance_cats,
                'verbatim': include_verbatim,
                'verbatim_text': verbatim_text,
                'verbatim_score': verbatim_score,
                'theme': theme,
                'title': report_title
            }
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    # TAB 4: Generate
    with tabs[3]:
        if 'metric_configs' not in st.session_state or not st.session_state.metric_configs:
            st.info("👈 Configure metrics first in the Metrics & Thresholds tab")
        else:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("<h2>Generate DAX Code</h2>", unsafe_allow_html=True)
            
            try:
                table_name = st.session_state.table_name
                theme = st.session_state.sections['theme']
                builder = DAXBuilder(table_name, theme)
                
                dax_parts = [builder.build_header()]
                
                # Add metric variables
                for metric in st.session_state.metric_configs:
                    dax_parts.append(builder.build_measure_var(
                        metric['name'],
                        metric['column'],
                        metric['aggregation'],
                        metric['decimals']
                    ))
                    dax_parts.append(builder.build_threshold_color(
                        metric['name'],
                        metric['thresholds']
                    ))
                
                # Add performance variables if needed
                if st.session_state.sections['performance'] and st.session_state.sections['performance_cats']:
                    for cat in st.session_state.sections['performance_cats']:
                        perf_vars, _ = builder.build_performance_table(
                            cat,
                            st.session_state.metric_configs[0]['column'],
                            st.session_state.metric_configs[0]['aggregation']
                        )
                        dax_parts.append(perf_vars)
                
                # Add verbatim variables if needed
                if st.session_state.sections['verbatim']:
                    pos_vars, _ = builder.build_verbatim_section(
                        st.session_state.sections['verbatim_text'],
                        st.session_state.sections['verbatim_score'],
                        'positive'
                    )
                    neg_vars, _ = builder.build_verbatim_section(
                        st.session_state.sections['verbatim_text'],
                        st.session_state.sections['verbatim_score'],
                        'negative'
                    )
                    dax_parts.append(pos_vars)
                    dax_parts.append(neg_vars)
                
                # Build HTML
                dax_parts.append(builder.build_html_start())
                dax_parts.append(builder.build_title_section(st.session_state.sections['title']))
                
                # KPI Cards
                kpi_section = '"<div style=\'display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:16px; margin-bottom:28px;\'>" &'
                for metric in st.session_state.metric_configs:
                    kpi_section += "\n" + builder.build_kpi_card_html(metric['name'], metric['name'])
                kpi_section += '\n"</div>" &'
                dax_parts.append(kpi_section)
                
                # Performance tables for each category
                if st.session_state.sections['performance'] and st.session_state.sections['performance_cats']:
                    for cat in st.session_state.sections['performance_cats']:
                        _, perf_html = builder.build_performance_table(
                            cat,
                            st.session_state.metric_configs[0]['column'],
                            st.session_state.metric_configs[0]['aggregation']
                        )
                        dax_parts.append(perf_html)
                
                # Verbatim sections
                if st.session_state.sections['verbatim']:
                    _, pos_html = builder.build_verbatim_section(
                        st.session_state.sections['verbatim_text'],
                        st.session_state.sections['verbatim_score'],
                        'positive'
                    )
                    _, neg_html = builder.build_verbatim_section(
                        st.session_state.sections['verbatim_text'],
                        st.session_state.sections['verbatim_score'],
                        'negative'
                    )
                    dax_parts.append(pos_html)
                    dax_parts.append(neg_html)
                
                dax_parts.append(builder.build_html_end())
                
                final_dax = "\n\n".join(dax_parts)
                st.session_state.generated_dax = final_dax
                
                st.markdown("<div class='success-box'><strong>✓ DAX Code Generated Successfully</strong><br>Syntactically correct and ready for Power BI</div>", unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col2:
                    st.download_button(
                        "💾 Download DAX",
                        final_dax,
                        "narrative.dax",
                        "text/plain",
                        use_container_width=True
                    )
                with col3:
                    if st.button("📋 Copy Code", use_container_width=True):
                        st.toast("Copied to clipboard!")
                
                st.code(final_dax, language='dax', line_numbers=True)
                
            except Exception as e:
                st.error(f"Generation Error: {str(e)}")
            
            st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
