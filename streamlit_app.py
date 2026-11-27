import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ロット管理", layout="wide")
JST = ZoneInfo("Asia/Tokyo")
R_FILE = "raw_materials.csv"
P_FILE = "production_batches.csv"
MATS = ["小麦粉", "液卵", "イースト", "乳化剤", "全粒粉"]
UNITS = ["kg", "g", "L", "mL", "袋", "箱", "本"]
R_COLS = ["受入日時", "原料名", "ロットNo", "仕入先", "受入数量", "単位", "賞味期限", "状態"]
P_COLS = ["仕込み日時", "製品名", "製造ロットNo", "使用原料", "原料ロットNo", "使用数量", "単位", "担当者"]


def load_df(path, cols):
    if os.path.exists(path):
        return pd.read_csv(path, dtype=str)
    return pd.DataFrame(columns=cols)


def add_row(path, cols, row):
    df = load_df(path, cols)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


st.title("食品工場 ロット紐づけ管理")
t1, t2, t3 = st.tabs(["1.原料受入", "2.仕込み紐づけ", "3.追跡・一覧"])

with t1:
    with st.form("f_recv", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        m_name = c1.selectbox("原料名", MATS)
        supp = c1.text_input("仕入先")
        lot = c2.text_input("原料ロットNo")
        exp = c2.date_input("賞味期限", value=datetime.now(JST).date())
        qty = c3.number_input("数量", min_value=0.1, value=25.0, step=0.5)
        unit = c3.selectbox("単位", UNITS)
        ok1 = st.form_submit_button("受入登録", type="primary")

    if ok1:
        if not lot.strip():
            st.error("ロットNoを入力してください")
        else:
            now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
            row = {
                "受入日時": now,
                "原料名": m_name,
                "ロットNo": lot.strip(),
                "仕入先": supp.strip(),
                "受入数量": qty,
                "単位": unit,
                "賞味期限": str(exp),
                "状態": "使用中",
            }
            add_row(R_FILE, R_COLS, row)
            st.success(f"登録完了: {m_name} ({lot.strip()})")

    df_r = load_df(R_FILE, R_COLS)
    st.dataframe(df_r, use_container_width=True, hide_index=True)

with t2:
    df_r = load_df(R_FILE, R_COLS)
    act = df_r[df_r["状態"] == "使用中"]
    col1, col2 = st.columns(2)
    sel_m = col1.selectbox("1.原料名", MATS)
    sub = act[act["原料名"] == sel_m]

    if sub.empty:
        col2.warning(f"{sel_m}の在庫ロットがありません")
        sel_lot = None
    else:
        lots = sub["ロットNo"].tolist()
        sel_lot = col2.selectbox("2.原料ロットNo", lots)

    if sel_lot:
        with st.form("f_prep", clear_on_submit=True):
            p1, p2, p3 = st.columns(3)
            prod = p1.text_input("製品名")
            d_lot = f"PRD-{datetime.now(JST).strftime('%Y%m%d')}-01"
            p_lot = p1.text_input("製造ロットNo", value=d_lot)
            u_qty = p2.number_input("使用量", min_value=0.1, value=10.0, step=0.5)
            u_unit = p2.selectbox("単位", UNITS)
            staff = p3.text_input("担当者")
            done = p3.checkbox("このロットを使い切りにする")
            ok2 = st.form_submit_button("紐づけ登録", type="primary")

        if ok2:
            if not prod.strip() or not p_lot.strip():
                st.error("製品名と製造ロットNoを入力してください")
            else:
                now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
                prow = {
                    "仕込み日時": now,
                    "製品名": prod.strip(),
                    "製造ロットNo": p_lot.strip(),
                    "使用原料": sel_m,
                    "原料ロットNo": sel_lot,
                    "使用数量": u_qty,
                    "単位": u_unit,
                    "担当者": staff.strip(),
                }
                add_row(P_FILE, P_COLS, prow)
                if done:
                    idx = (df_r["原料名"] == sel_m) & (df_r["ロットNo"] == sel_lot)
                    df_r.loc[idx, "状態"] = "使用済"
                    df_r.to_csv(R_FILE, index=False, encoding="utf-8-sig")
                st.success(f"紐づけ完了: {p_lot.strip()} <= {sel_m}({sel_lot})")

with t3:
    df_p = load_df(P_FILE, P_COLS)
    kw = st.text_input("検索（製品名・製造ロットNo・原料ロットNo）")
    if kw.strip() and not df_p.empty:
        k = kw.strip()
        m = (
            df_p["製品名"].str.contains(k, na=False)
            | df_p["製造ロットNo"].str.contains(k, na=False)
            | df_p["原料ロットNo"].str.contains(k, na=False)
        )
        df_p = df_p[m]
    st.dataframe(df_p, use_container_width=True, hide_index=True)
    csv = df_p.to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSVダウンロード", csv, "trace.csv", "text/csv")
