import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

st.set_page_config(page_title="食品工場 ロット管理", layout="wide")

JST = ZoneInfo("Asia/Tokyo")
RECV_FILE = "raw_materials.csv"
PREP_FILE = "production_batches.csv"

MATERIAL_LIST = ["小麦粉", "液卵", "イースト", "乳化剤", "全粒粉"]
UNIT_LIST = ["kg", "g", "L", "mL", "袋", "箱", "本"]

RECV_COLS = [
    "受入ID",
    "受入日時",
    "受入日",
    "原料名",
    "ロットNo",
    "仕入先",
    "受入数量",
    "単位",
    "賞味期限",
    "ステータス",
]

PREP_COLS = [
    "仕込みID",
    "仕込み日時",
    "仕込み日",
    "製品名",
    "製造ロットNo",
    "使用原料名",
    "使用原料ロットNo",
    "使用数量",
    "単位",
    "担当者",
]


def load_csv(file_path, columns):
    if os.path.exists(file_path):
        dtypes = {"ロットNo": str, "製造ロットNo": str, "使用原料ロットNo": str}
        return pd.read_csv(file_path, dtype=dtypes)
    return pd.DataFrame(columns=columns)


def append_csv(file_path, columns, record):
    df = load_csv(file_path, columns)
    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df.to_csv(file_path, index=False, encoding="utf-8-sig")


def update_recv_status(material_name, lot_no, new_status):
    df = load_csv(RECV_FILE, RECV_COLS)
    mask = (df["原料名"] == material_name) & (df["ロットNo"] == lot_no)
    df.loc[mask, "ステータス"] = new_status
    df.to_csv(RECV_FILE, index=False, encoding="utf-8-sig")


st.title("食品工場 原料受入・仕込みロット管理")
st.caption("原料受入ロットの登録と、仕込み時のロット紐づけ・追跡を行います。")

tab_recv, tab_prep, tab_trace = st.tabs([
    "1. 原料受入登録",
    "2. 仕込み・ロット紐づけ",
    "3. ロット追跡・一覧",
])

# ==========================================
# タブ1：原料受入時のロット登録
# ==========================================
with tab_recv:
    st.subheader("原料受入・ロットNo 登録")
    with st.form("receive_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            mat_name = st.selectbox("原料名", MATERIAL_LIST)
            supplier = st.text_input("仕入先", placeholder="例：〇〇製粉")
        with c2:
            lot_no = st.text_input("原料ロットNo", placeholder="例：LOT-20261127-A")
            exp_date = st.date_input("賞味期限", value=datetime.now(JST).date())
        with c3:
            qty = st.number_input("受入数量", min_value=0.1, value=25.0, step=0.5)
            unit = st.selectbox("単位", UNIT_LIST)

        submitted_recv = st.form_submit_button("受入データを登録する", type="primary")

    if submitted_recv:
        if not lot_no.strip():
            st.error("原料ロットNoを入力してください。")
        else:
            now_jst = datetime.now(JST)
            record = {
                "受入ID": f"RCV-{now_jst.strftime('%Y%m%d%H%M%S')}",
                "受入日時": now_jst.strftime("%Y-%m-%d %H:%M:%S"),
                "受入日": now_jst.strftime("%Y-%m-%d"),
                "原料名": mat_name,
                "ロットNo": lot_no.strip(),
                "仕入先": supplier.strip(),
                "受入数量": qty,
                "単位": unit,
                "賞味期限": exp_date.strftime("%Y-%m-%d"),
                "ステータス": "使用中",
            }
            append_csv(RECV_FILE, RECV_COLS, record)
            st.success(f"受入登録完了：{mat_name}（ロット: {lot_no.strip()} / {qty}{unit}）")

    st.divider()
    st.markdown("**現在の受入原料一覧**")
    df_recv_view = load_csv(RECV
