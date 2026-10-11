"""
MoveInSync Play Store Ratings Analysis — Streamlit Dashboard

Interactive dashboard for exploring review themes, trends, and competitor benchmarks.
"""
import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import psycopg2
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(database_url)


@st.cache_data(ttl=300)
def load_data():
    """Load all labeled reviews into a DataFrame."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT
            r.review_id, r.rating, r.text, r.lang, r.review_date,
            r.app_version, r.thumbs_up, r.dev_reply, r.dev_reply_date,
            l.primary_theme, l.themes, l.sentiment, l.severity,
            l.attribution, l.evidence_span, l.confidence,
            a.name as app_name, a.role as app_role, a.package_id
        FROM reviews r
        JOIN labels l ON r.review_id = l.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE l.status IN ('auto', 'human')
    """, conn)
    conn.close()

    df['review_date'] = pd.to_datetime(df['review_date'])
    df['quarter'] = df['review_date'].dt.to_period('Q').astype(str)
    df['month'] = df['review_date'].dt.to_period('M').astype(str)
    df['has_reply'] = df['dev_reply'].notna()
    return df


# ─── Page Config ───
st.set_page_config(
    page_title="MoveInSync Ratings Analysis",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ───
st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    .stMetric { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                padding: 1rem; border-radius: 10px; border: 1px solid #0f3460; }
    h1, h2, h3 { color: #e94560; }
    .stSelectbox label, .stMultiSelect label { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─── Load Data ───
try:
    df = load_data()
except Exception as e:
    st.error(f"Database connection error: {e}")
    st.stop()

# ─── Sidebar ───
with st.sidebar:
    st.title("🚗 MoveInSync Analysis")
    st.markdown("---")

    # App filter
    app_options = df['app_name'].unique().tolist()
    selected_apps = st.multiselect("Apps", app_options, default=app_options)

    # Rating filter
    rating_range = st.slider("Rating Range", 1, 5, (1, 5))

    # Date filter
    min_date = df['review_date'].min().date()
    max_date = df['review_date'].max().date()
    date_range = st.date_input("Date Range", value=(min_date, max_date),
                                min_value=min_date, max_value=max_date)

    st.markdown("---")
    st.markdown(f"**Total reviews:** {len(df):,}")
    st.markdown(f"**Date range:** {min_date} → {max_date}")

# ─── Apply Filters ───
mask = (
    df['app_name'].isin(selected_apps) &
    df['rating'].between(rating_range[0], rating_range[1])
)
if len(date_range) == 2:
    mask &= (df['review_date'].dt.date >= date_range[0]) & \
            (df['review_date'].dt.date <= date_range[1])

filtered = df[mask]

# ─── Header Metrics ───
st.title("📊 Play Store Ratings Analysis")
st.markdown("*Root-cause diagnosis of review themes, trends, and competitor benchmarks*")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Reviews", f"{len(filtered):,}")
with col2:
    avg_rating = filtered['rating'].mean()
    st.metric("Avg Rating", f"{avg_rating:.2f}")
with col3:
    neg_pct = (filtered['rating'] <= 2).mean() * 100
    st.metric("Negative %", f"{neg_pct:.1f}%")
with col4:
    reply_rate = filtered['has_reply'].mean() * 100
    st.metric("Reply Rate", f"{reply_rate:.1f}%")
with col5:
    unique_themes = filtered['primary_theme'].nunique()
    st.metric("Themes", unique_themes)

st.markdown("---")

# ─── Tab Layout ───
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Theme Analysis", "📈 Trends", "🏆 Competitors",
    "🔧 Version Analysis", "📋 Raw Reviews"
])

# ─── Tab 1: Theme Analysis ───
with tab1:
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Theme Distribution (Negative Reviews)")
        neg = filtered[filtered['rating'] <= 2]
        if len(neg) > 0:
            theme_counts = neg['primary_theme'].value_counts().reset_index()
            theme_counts.columns = ['Theme', 'Count']
            fig = px.bar(theme_counts, x='Count', y='Theme', orientation='h',
                        color='Count', color_continuous_scale='Reds',
                        title=f"Top complaint themes (1-2 star reviews, n={len(neg)})")
            fig.update_layout(yaxis={'categoryorder': 'total ascending'},
                            height=500, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No negative reviews match the current filters.")

    with col_right:
        st.subheader("Attribution Split")
        if len(neg) > 0:
            attr_counts = neg['attribution'].value_counts().reset_index()
            attr_counts.columns = ['Attribution', 'Count']
            fig = px.pie(attr_counts, values='Count', names='Attribution',
                        color='Attribution',
                        color_discrete_map={
                            'app': '#e94560', 'ops_vendor': '#0f3460',
                            'customer_policy': '#533483', 'unclear': '#999'
                        },
                        title="Who owns the problem?")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Severity Breakdown")
        if len(neg) > 0:
            sev_counts = neg['severity'].value_counts().sort_index().reset_index()
            sev_counts.columns = ['Severity', 'Count']
            sev_counts['Label'] = sev_counts['Severity'].map(
                {1: '1 - Minor', 2: '2 - Significant', 3: '3 - Blocking/Safety'})
            fig = px.bar(sev_counts, x='Label', y='Count', color='Severity',
                        color_continuous_scale='OrRd')
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

# ─── Tab 2: Trends ───
with tab2:
    st.subheader("Theme Trends Over Time")

    # MIS employee only for trend
    mis = filtered[filtered['package_id'] == 'com.moveinsync.ets']
    if len(mis) > 0:
        trend = mis.groupby(['quarter', 'primary_theme']).size().reset_index(name='count')

        # Top 5 themes by total
        top_themes = mis['primary_theme'].value_counts().head(5).index.tolist()
        trend_top = trend[trend['primary_theme'].isin(top_themes)]

        fig = px.line(trend_top, x='quarter', y='count', color='primary_theme',
                     markers=True, title="Theme frequency by quarter (MIS Employee)")
        fig.update_layout(height=500, xaxis_title="Quarter", yaxis_title="Review Count")
        st.plotly_chart(fig, use_container_width=True)

    # Rating trend
    st.subheader("Rating Trend")
    if len(mis) > 0:
        rating_trend = mis.groupby('quarter')['rating'].agg(['mean', 'count']).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=rating_trend['quarter'], y=rating_trend['mean'],
                                mode='lines+markers', name='Avg Rating',
                                line=dict(color='#e94560', width=3)))
        fig.add_trace(go.Bar(x=rating_trend['quarter'], y=rating_trend['count'],
                            name='Review Count', opacity=0.3, yaxis='y2'))
        fig.update_layout(
            yaxis=dict(title='Average Rating', range=[1, 5]),
            yaxis2=dict(title='Review Count', overlaying='y', side='right'),
            height=400, title="Average rating and review volume over time"
        )
        st.plotly_chart(fig, use_container_width=True)

# ─── Tab 3: Competitors ───
with tab3:
    st.subheader("Competitor Benchmarking")

    # Compare negative theme distributions
    neg_all = filtered[filtered['rating'] <= 2]
    if len(neg_all) > 0:
        comp = neg_all.groupby(['app_name', 'primary_theme']).size().reset_index(name='count')
        # Normalize within each app
        totals = comp.groupby('app_name')['count'].sum().reset_index(name='total')
        comp = comp.merge(totals, on='app_name')
        comp['pct'] = (comp['count'] / comp['total'] * 100).round(1)

        fig = px.bar(comp, x='primary_theme', y='pct', color='app_name',
                    barmode='group', title="Negative theme share (%) by app")
        fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # Reply rate comparison
    st.subheader("Developer Reply Rate")
    reply = filtered.groupby('app_name').agg(
        total=('review_id', 'count'),
        replied=('has_reply', 'sum'),
        avg_rating=('rating', 'mean')
    ).reset_index()
    reply['reply_rate'] = (reply['replied'] / reply['total'] * 100).round(1)
    st.dataframe(reply.sort_values('reply_rate', ascending=False), use_container_width=True)

# ─── Tab 4: Version Analysis ───
with tab4:
    st.subheader("Rating by App Version")

    mis = filtered[filtered['package_id'] == 'com.moveinsync.ets']
    if len(mis) > 0 and 'app_version' in mis.columns:
        version_stats = mis[mis['app_version'].notna()].groupby('app_version').agg(
            count=('review_id', 'count'),
            avg_rating=('rating', 'mean'),
        ).reset_index()
        version_stats = version_stats[version_stats['count'] >= 5].sort_values('app_version')

        fig = go.Figure()
        fig.add_trace(go.Bar(x=version_stats['app_version'], y=version_stats['count'],
                            name='Review Count', opacity=0.4))
        fig.add_trace(go.Scatter(x=version_stats['app_version'], y=version_stats['avg_rating'],
                                mode='lines+markers', name='Avg Rating', yaxis='y2',
                                line=dict(color='#e94560', width=3)))
        fig.update_layout(
            yaxis=dict(title='Count'),
            yaxis2=dict(title='Avg Rating', overlaying='y', side='right', range=[1, 5]),
            height=500, title="Version-level rating analysis (MIS Employee)"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Theme breakdown per version
        st.subheader("Theme Breakdown by Version")
        version_theme = mis[mis['app_version'].notna()].groupby(
            ['app_version', 'primary_theme']
        ).size().reset_index(name='count')
        top_versions = version_stats.nlargest(8, 'count')['app_version'].tolist()
        vt_filtered = version_theme[version_theme['app_version'].isin(top_versions)]

        fig = px.bar(vt_filtered, x='app_version', y='count', color='primary_theme',
                    title="Theme distribution for top versions")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

# ─── Tab 5: Raw Reviews ───
with tab5:
    st.subheader("Browse Reviews")

    col1, col2 = st.columns(2)
    with col1:
        theme_filter = st.selectbox("Filter by Theme",
                                     ["All"] + sorted(filtered['primary_theme'].unique().tolist()))
    with col2:
        attr_filter = st.selectbox("Filter by Attribution",
                                    ["All"] + sorted(filtered['attribution'].dropna().unique().tolist()))

    browsed = filtered.copy()
    if theme_filter != "All":
        browsed = browsed[browsed['primary_theme'] == theme_filter]
    if attr_filter != "All":
        browsed = browsed[browsed['attribution'] == attr_filter]

    browsed = browsed.sort_values('thumbs_up', ascending=False)

    st.dataframe(
        browsed[['rating', 'primary_theme', 'attribution', 'severity', 'text',
                 'app_version', 'app_name', 'review_date', 'has_reply']].head(100),
        use_container_width=True,
        height=600
    )

# ─── Footer ───
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85em;'>
    MoveInSync Play Store Ratings Analysis | Data from google-play-scraper |
    Classification by Gemini 2.5 Flash | Built for hiring case study
</div>
""", unsafe_allow_html=True)
