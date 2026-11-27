import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="日本の労働災害データ分析 (2024-2025)", layout="wide")
st.title("日本の労働災害データ分析（2024年・2025年確定値）")

# 1. 集計データの読み込み（サンプルとして確定値をDataFrame化・実際はCSV/Excel読込）
@st.cache_data
def load_summary_data():
    data = [
        {"年": "2024年", "業種": "建設業", "死亡者数": 232, "死傷者数": 13849},
        {"年": "2025年", "業種": "建設業", "死亡者数": 214, "死傷者数": 13437},
        {"年": "2024年", "業種": "製造業", "死亡者数": 142, "死傷者数": 26676},
        {"年": "2025年", "業種": "製造業", "死亡者数": 115, "死傷者数": 26371},
        {"年": "2024年", "業種": "陸上貨物運送事業", "死亡者数": 108, "死傷者数": 16292},
        {"年": "2025年", "業種": "陸上貨物運送事業", "死亡者数": 80, "死傷者数": 15632},
        {"年": "2024年", "業種": "第三次産業", "死亡者数": 194, "死傷者数": 71454},
        {"年": "2025年", "業種": "第三次産業", "死亡者数": 197, "死傷者数": 71878},
    ]
    return pd.DataFrame(data)

# 2. 事例データベースの読み込み（職場のあんぜんサイトから取得したCSVを想定）
@st.cache_data
def load_cases_data():
    # 実際は pd.read_csv("data/cases_database.csv", encoding="utf-8") を使用
    sample_cases = [
        {
            "発生年": "2024年",
            "業種": "建設業",
            "事故の型": "墜落・転落",
            "起因物": "足場",
            "発生状況": "ビルの外壁塗装工事中、枠組足場の2層目から足を踏み外し約4メートル下の地面に墜落した。"
        },
        {
            "発生年": "2024年",
            "業種": "製造業",
            "事故の型": "はさまれ・巻き込まれ",
            "起因物": "コンベヤ",
            "発生状況": "稼働中のベルトコンベヤのローラー付近に付着した異物を除去しようとして右手が巻き込まれた。"
        },
        {
            "発生年": "2025年",
            "業種": "第三次産業",
            "事故の型": "転倒",
            "起因物": "通路",
            "発生状況": "スーパーマーケットのバックヤードで、水濡れしていた床面に足を滑らせ転倒し手首を骨折した。"
        },
        {
            "発生年": "2025年",
            "業種": "陸上貨物運送事業",
            "事故の型": "墜落・転落",
            "起因物": "トラック",
            "発生状況": "荷台上で荷締め作業を行っていた際、バランスを崩して地面に転落した。"
        },
    ]
    return pd.DataFrame(sample_cases)

df_summary = load_summary_data()
df_cases = load_cases_data()

# --- タブ構成 ---
tab1, tab2 = st.tabs(["📊 2024・2025年 統計グラフ", "🔍 事故事例の抽出・検索"])

with tab1:
    st.subheader("主要業種別の労働災害推移（2024年 vs 2025年）")
    metric = st.radio("表示する指標を選択", ["死亡者数", "死傷者数"], horizontal=True)

    fig = px.bar(
        df_summary,
        x="業種",
        y=metric,
        color="年",
        barmode="group",
        text_auto=True,
        title=f"業種別 {metric} の年次比較",
        color_discrete_map={"2024年": "#636EFA", "2025年": "#EF553B"}
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("労働災害事例の条件フィルタリング")
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_years = st.multiselect("発生年", df_cases["発生年"].unique(), default=df_cases["発生年"].unique())
    with col2:
        selected_industries = st.multiselect("業種", df_cases["業種"].unique(), default=df_cases["業種"].unique())
    with col3:
        keyword = st.text_input("発生状況のキーワード（例: 足場, ローラー, 転倒）", "")

    # フィルタ処理
    filtered_df = df_cases[
        (df_cases["発生年"].isin(selected_years)) &
        (df_cases["業種"].isin(selected_industries))
    ]
    if keyword:
        filtered_df = filtered_df[filtered_df["発生状況"].str.contains(keyword, na=False)]

    st.write(f"該当件数: **{len(filtered_df)} 件**")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # 抽出結果のCSVダウンロード
    csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="抽出した事例をCSVでダウンロード",
        data=csv_data,
        file_name="extracted_labor_accidents.csv",
        mime="text/csv"
    )
