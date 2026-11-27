import os
from datetime import datetime, date
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="食品工場 入場衛生チェック表", layout="wide")

JST = ZoneInfo("Asia/Tokyo")
DATA_FILE = "entry_logs.csv"
COLUMNS = [
    "記録日時", "日付", "時間帯", "部署", "氏名",
    "体温", "持ち込み禁止物", "怪我の有無", "判定", "備考"
]

# --- データ読み書き関数（実運用時はGoogleスプレッドシート等に差し替え推奨） ---
def load_data() -> pd.DataFrame:
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["日付"] = pd.to_datetime(df["日付"]).dt.date
        return df
    return pd.DataFrame(columns=COLUMNS)

def save_record(record: dict) -> None:
    df = load_data()
    new_df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    new_df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# --- ヘッダ ---
st.title("🏭 食品工場 入場衛生チェック表")
st.caption("入場前に必ず全項目を入力してください（37.5℃以上・禁止物あり・怪我ありの場合は管理者へ報告）。")

tab_input, tab_summary = st.tabs(["📝 入場チェック入力", "📊 日次・月次集計レポート"])

# ==========================================
# タブ1：入場チェック入力フォーム
# ==========================================
with tab_input:
    with st.form("entry_check_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            department = st.selectbox(
                "部署・製造ライン",
                ["下処理・原料", "加熱・調理", "包装・充填", "検品・出荷", "品質管理・事務所", "外部業者・来客"]
            )
        with col2:
            worker_name = st.text_input("氏名（フルネーム）", placeholder="例：山田 太郎")

        st.divider()

        col_temp, col_item, col_injury = st.columns(3)
        with col_temp:
            temperature = st.number_input(
                "体温（℃）",
                min_value=34.0,
                max_value=42.0,
                value=36.5,
                step=0.1,
                format="%.1f"
            )
        with col_item:
            prohibited_items = st.radio(
                "持ち込み禁止物の有無（時計・指輪・スマホ等）",
                options=["なし", "あり"],
                horizontal=True
            )
        with col_injury:
            injury_status = st.radio(
                "手指の怪我・皮膚異常の有無",
                options=["なし", "あり"],
                horizontal=True
            )

        remarks = st.text_input("備考（怪我の箇所・絆創膏の装着状況・体調など）", placeholder="特記事項があれば入力")

        submitted = st.form_submit_button("✅ チェックを登録する", type="primary", use_container_width=True)

    if submitted:
        if not worker_name.strip():
            st.error("氏名を入力してください。")
        else:
            now_jst = datetime.now(JST)
            # 基準判定
            is_ng = (temperature >= 37.5) or (prohibited_items == "あり") or (injury_status == "あり")
            judgment = "要確認（保留）" if is_ng else "入場可"

            record = {
                "記録日時": now_jst.strftime("%Y-%m-%d %H:%M:%S"),
                "日付": now_jst.date(),
                "時間帯": f"{now_jst.hour:02d}時台",
                "部署": department,
                "氏名": worker_name.strip(),
                "体温": round(temperature, 1),
                "持ち込み禁止物": prohibited_items,
                "怪我の有無": injury_status,
                "判定": judgment,
                "備考": remarks.strip()
            }
            save_record(record)

            if is_ng:
                st.error(
                    f"⚠️ **【要確認】{worker_name.strip()} さん**：基準外項目があります（体温: {temperature:.1f}℃ / 禁止物: {prohibited_items} / 怪我: {injury_status}）。現場責任者の確認を受けてください。"
                )
            else:
                st.success(f"🙆‍♂️ **【入場可】{worker_name.strip()} さん**（{now_jst.strftime('%H:%M')} 登録完了）")

# ==========================================
# タブ2：集計・履歴確認
# ==========================================
with tab_summary:
    df = load_data()

    if df.empty:
        st.info("まだ記録がありません。「入場チェック入力」タブからデータを登録してください。")
    else:
        # 期間フィルタ
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            target_date = st.date_input("集計対象日", value=datetime.now(JST).date())
        with col_f2:
            filter_dept = st.multiselect("部署絞り込み", options=df["部署"].unique(), default=df["部署"].unique())

        daily_df = df[(df["日付"] == target_date) & (df["部署"].isin(filter_dept))]

        # KPIメトリクス表示
        st.subheader(f"{target_date.strftime('%Y年%m月%d日')} の入場サマリー")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("総入場チェック数", f"{len(daily_df)} 名")
        m2.metric("入場可", f"{(daily_df['判定'] == '入場可').sum()} 名")
        m3.metric("要確認（保留）", f"{(daily_df['判定'] == '要確認（保留）').sum()} 名")
        m4.metric("禁止物あり", f"{(daily_df['持ち込み禁止物'] == 'あり').sum()} 件")
        m5.metric("怪我あり", f"{(daily_df['怪我の有無'] == 'あり').sum()} 件")

        st.divider()

        # グラフと要確認者リスト
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("**部署別 チェック人数**")
            dept_counts = daily_df.groupby(["部署", "判定"], as_index=False).size()
            fig_dept = px.bar(
                dept_counts, x="部署", y="size", color="判定",
                barmode="stack", text_auto=True,
                labels={"size": "人数"},
                color_discrete_map={"入場可": "#2E8B57", "要確認（保留）": "#DC143C"}
            )
            st.plotly_chart(fig_dept, use_container_width=True)

        with col_chart2:
            st.markdown("**要確認（保留）対象者リスト**")
            ng_df = daily_df[daily_df["判定"] == "要確認（保留）"]
            if ng_df.empty:
                st.success("対象日の要確認者はいません。")
            else:
                st.dataframe(
                    ng_df[["記録日時", "部署", "氏名", "体温", "持ち込み禁止物", "怪我の有無", "備考"]],
                    use_container_width=True,
                    hide_index=True
                )

        # 全履歴テーブルとCSVダウンロード
        st.subheader("全記録一覧・CSV出力")
        st.dataframe(daily_df.sort_values("記録日時", ascending=False), use_container_width=True, hide_index=True)

        csv_bytes = daily_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 対象日の記録をCSVダウンロード",
            data=csv_bytes,
            file_name=f"entry_check_{target_date}.csv",
            mime="text/csv"
        )
