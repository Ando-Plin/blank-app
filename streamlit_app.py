import os
from datetime import datetime, date
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

st.set_page_config(page_title="食品工場 原料受入・仕込みトレーサビリティ", layout="wide")

JST = ZoneInfo("Asia/Tokyo")
RECV_FILE = "raw_materials.csv"
PREP_FILE = "production_batches.csv"

RECV_COLS = [
    "受入ID", "受入日時", "受入日", "原料名", "ロットNo",
    "仕入先", "受入数量", "単位", "賞味期限", "ステータス"
]
PREP_COLS = [
    "仕込みID", "仕込み日時", "仕込み日", "製品名", "製造ロットNo",
    "使用原料名", "使用原料ロットNo", "使用数量", "単位", "担当者"
]

# --- データ読み書き関数 ---
def load_csv(file_path: str, columns: list[str]) -> pd.DataFrame:
    if os.path.exists(file_path):
        return pd.read_csv(file_path, dtype={"ロットNo": str, "製造ロットNo": str, "使用原料ロットNo": str})
    return pd.DataFrame(columns=columns)

def append_csv(file_path: str, columns: list[str], record: dict) -> None:
    df = load_csv(file_path, columns)
    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df.to_csv(file_path, index=False, encoding="utf-8-sig")

def update_recv_status(material_name: str, lot_no: str, new_status: str) -> None:
    df = load_csv(RECV_FILE, RECV_COLS)
    mask = (df["原料名"] == material_name) & (df["ロットNo"] == lot_no)
    df.loc[mask, "ステータス"] = new_status
    df.to_csv(RECV_FILE, index=False, encoding="utf-8-sig")

# --- ヘッダ ---
st.title("📦 食品工場 原料受入・仕込みロット紐づけ管理")
st.caption("原料受入時のロット登録から、製造仕込み時の使用ロット紐づけ・トレース検索まで一元管理します。")

tab_recv, tab_prep, tab_trace = st.tabs([
    "1️⃣ 原料受入登録",
    "2️⃣ 仕込み・ロット紐づけ",
    "🔍 トレーサビリティ検索・一覧"
])

# ==========================================
# タブ1：原料受入時のロット登録
# ==========================================
with tab_recv:
    st.subheader("原料受入・ロット№ 登録")
    with st.form("receive_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            mat_name = st.text_input("原料名", placeholder="例：強力粉（国産）")
            supplier = st.text_input("仕入先・メーカー", placeholder="例：〇〇製粉")
        with c2:
            lot_no = st.text_input("原料ロット№", placeholder="例：LOT-20261127-A")
            exp_date = st.date_input("賞味期限", value=datetime.now(JST).date())
        with c3:
            qty = st.number_input("受入数量", min_value=0.1, value=25.0, step=0.5, format="%.1f")
            unit = st.selectbox("単位", ["kg", "g", "L", "mL", "袋", "箱", "本"])

        submitted_recv = st.form_submit_button("📥 受入データを登録する", type="primary", use_container_width=True)

    if submitted_recv:
        if not mat_name.strip() or not lot_no.strip():
            st.error("「原料名」と「原料ロット№」は必須項目です。")
        else:
            now_jst = datetime.now(JST)
            record = {
                "受入ID": f"RCV-{now_jst.strftime('%Y%m%d%H%M%S')}",
                "受入日時": now_jst.strftime("%Y-%m-%d %H:%M:%S"),
                "受入日": now_jst.strftime("%Y-%m-%d"),
                "原料名": mat_name.strip(),
                "ロットNo": lot_no.strip(),
                "仕入先": supplier.strip(),
                "受入数量": qty,
                "単位": unit,
                "賞味期限": exp_date.strftime("%Y-%m-%d"),
                "ステータス": "使用中"
            }
            append_csv(RECV_FILE, RECV_COLS, record)
            st.success(f"✅ 受入登録完了：**{mat_name.strip()}**（ロット№: `{lot_no.strip()}` / {qty}{unit}）")

    st.divider()
    st.markdown("**現在の受入原料一覧**")
    df_recv_view = load_csv(RECV_FILE, RECV_COLS)
    if df_recv_view.empty:
        st.info("受入データは未登録です。")
    else:
        st.dataframe(df_recv_view.sort_values("受入日時", ascending=False), use_container_width=True, hide_index=True)

# ==========================================
# タブ2：仕込み時の原料・ロット紐づけ記録
# ==========================================
with tab_prep:
    st.subheader("仕込み記録（製造ロット × 原料ロット紐づけ）")
    df_recv = load_csv(RECV_FILE, RECV_COLS)
    active_recv = df_recv[df_recv["ステータス"] == "使用中"]

    if active_recv.empty:
        st.warning("使用可能な受入原料が登録されていません。先に「1️⃣ 原料受入登録」から原料を登録してください。")
    else:
        # フォーム外で原料を選択し、該当するロット№だけを動的に絞り込む
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            available_materials = sorted(active_recv["原料名"].unique())
            selected_mat = st.selectbox("① 使用する原料名を選択", available_materials)

        with col_sel2:
            mat_lots_df = active_recv[active_recv["原料名"] == selected_mat]
            # ロット№と受入日・賞味期限を分かりやすく表示
            lot_options = {
                f"{row['ロットNo']}（受入:{row['受入日']} / 期限:{row['賞味期限']}）": row["ロットNo"]
                for _, row in mat_lots_df.iterrows()
            }
            selected_lot_label = st.selectbox("② 使用する原料ロット№を選択", list(lot_options.keys()))
            selected_lot_no = lot_options[selected_lot_label]

        # 選択されたロットの単位を取得
        default_unit = mat_lots_df[mat_lots_df["ロットNo"] == selected_lot_no]["単位"].iloc[0]

        with st.form("prep_form", clear_on_submit=True):
            p1, p2, p3 = st.columns(3)
            with p1:
                product_name = st.text_input("製造する製品名", placeholder="例：食パン生地A")
                batch_lot = st.text_input(
                    "製品側の製造ロット№（仕込みバッチ）",
                    value=f"PRD-{datetime.now(JST).strftime('%Y%m%d')}-01"
                )
            with p2:
                use_qty = st.number_input("使用数量", min_value=0.1, value=10.0, step=0.5, format="%.1f")
                use_unit = st.selectbox("単位", ["kg", "g", "L", "mL", "袋", "箱", "本"],
                                        index=["kg", "g", "L", "mL", "袋", "箱", "本"].index(default_unit)
                                        if default_unit in ["kg", "g", "L", "mL", "袋", "箱", "本"] else 0)
            with p3:
                operator = st.text_input("仕込み担当者", placeholder="例：佐藤")
                mark_finished = st.checkbox("この原料ロットを「使い切り（使用済）」にする")

            submitted_prep = st.form_submit_button("🔗 仕込み・ロット紐づけを登録する", type="primary", use_container_width=True)

        if submitted_prep:
            if not product_name.strip() or not batch_lot.strip():
                st.error("「製品名」と「製品側の製造ロット№」を入力してください。")
            else:
                now_jst = datetime.now(JST)
                prep_record = {
                    "仕込みID": f"PRP-{now_jst.strftime('%Y%m%d%H%M%S')}",
                    "仕込み日時": now_jst.strftime("%Y-%m-%d %H:%M:%S"),
                    "仕込み日": now_jst.strftime("%Y-%m-%d"),
                    "製品名": product_name.strip(),
                    "製造ロットNo": batch_lot.strip(),
                    "使用原料名": selected_mat,
                    "使用原料ロットNo": selected_lot_no,
                    "使用数量": use_qty,
                    "単位": use_unit,
                    "担当者": operator.strip()
                }
                append_csv(PREP_FILE, PREP_COLS, prep_record)

                if mark_finished:
                    update_recv_status(selected_mat, selected_lot_no, "使用済")

                st.success(
                    f"🔗 紐づけ登録完了：製品 **{product_name.strip()}**（製造ロット: `{batch_lot.strip()}`） ⇐ 原料 **{selected_mat}**（ロット: `{selected_lot_no}` / {use_qty}{use_unit}）"
                )

# ==========================================
# タブ3：トレーサビリティ検索（双方向追跡）
# ==========================================
with tab_trace:
    st.subheader("ロット追跡・履歴検索")
    df_recv_all = load_csv(RECV_FILE, RECV_COLS)
    df_prep_all = load_csv(PREP_FILE, PREP_COLS)

    if df_prep_all.empty:
        st.info("まだ仕込み・紐づけ記録がありません。")
    else:
        # 受入情報（仕入先・賞味期限）を結合した統合ビューを作成
        merged_df = pd.merge(
            df_prep_all,
            df_recv_all[["原料名", "ロットNo", "仕入先", "受入日", "賞味期限"]],
            left_on=["使用原料名", "使用原料ロットNo"],
            right_on=["原料名", "ロットNo"],
            how="left"
        ).drop(columns=["原料名", "ロットNo"])

        search_mode = st.radio(
            "検索方向を選択",
            ["製品ロットから使用原料を追跡（トレースバック）", "原料ロットから使用された製品を追跡（トレースフォワード）"],
            horizontal=True
        )
        keyword = st.text_input("ロット№ または 製品名・原料名で絞り込み", placeholder="一部入力でも検索できます")

        view_df = merged_df.copy()
        if keyword.strip():
            kw = keyword.strip()
            if "製品ロットから" in search_mode:
                view_df = view_df[
                    view_df["製造ロットNo"].str.contains(kw, na=False) |
                    view_df["製品名"].str.contains(kw, na=False)
                ]
            else:
                view_df = view_df[
                    view_df["使用原料ロットNo"].str.contains(kw, na=False) |
                    view_df["使用原料名"].str.contains(kw, na=False)
                ]

        st.write(f"該当件数: **{len(view_df)} 件**")
        st.dataframe(view_df.sort_values("仕込み日時", ascending=False), use_container_width=True, hide_index=True)

        # CSVダウンロード
        csv_out = view_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 紐づけ履歴をCSVダウンロード",
            data=csv_out,
            file_name=f"traceability_{datetime.now(JST).strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
