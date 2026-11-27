import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

st.set_page_config(page_title="トレーサビリティ", layout="wide")
JST = ZoneInfo("Asia/Tokyo")
R_FILE = "raw_materials.csv"
P_FILE = "production_batches.csv"
MATS = ["小麦粉", "液卵", "イースト", "乳化剤", "全粒粉"]
UNITS = ["kg", "g", "L", "mL", "袋", "箱", "本"]
STATUS_LIST = ["使用中", "使用済"]
R_COLS = ["受入日時", "原料名", "ロットNo", "仕入先", "受入数量", "単位", "賞味期限", "状態"]
P_COLS = ["仕込み日時", "製品名", "製造ロットNo", "使用原料", "原料ロットNo", "使用数量", "単位", "担当者"]


def load_df(path, cols):
    if os.path.exists(path):
        df = pd.read_csv(path, dtype=str)
        if list(df.columns) == cols:
            return df.fillna("")
    return pd.DataFrame(columns=cols)


def save_df(path, df):
    df.to_csv(path, index=False, encoding="utf-8-sig")


def add_row(path, cols, row):
    df = load_df(path, cols)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_df(path, df)


st.title("トレーサビリティ")
t1, t2, t3 = st.tabs(["1.原料受入", "2.仕込み紐づけ", "3.双方向トレース検索"])

# ==========================================
# タブ1：原料受入登録・編集
# ==========================================
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
                "受入数量": str(qty),
                "単位": unit,
                "賞味期限": str(exp),
                "状態": "使用中",
            }
            add_row(R_FILE, R_COLS, row)
            st.success(f"登録完了: {m_name} ({lot.strip()})")

    st.divider()
    st.subheader("受入一覧（セルを直接クリックして変更・行選択で削除可能）")
    df_r = load_df(R_FILE, R_COLS)
    if df_r.empty:
        st.info("受入データはまだありません")
    else:
        r_cfg = {
            "原料名": st.column_config.SelectboxColumn("原料名", options=MATS, required=True),
            "単位": st.column_config.SelectboxColumn("単位", options=UNITS, required=True),
            "状態": st.column_config.SelectboxColumn("状態", options=STATUS_LIST, required=True),
        }
        edited_r = st.data_editor(
            df_r,
            column_config=r_cfg,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="ed_recv",
        )
        if st.button("受入データの変更を保存", type="primary"):
            save_df(R_FILE, edited_r)
            st.success("受入データの変更を保存しました")
            st.rerun()

# ==========================================
# タブ2：仕込み紐づけ・編集
# ==========================================
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
                    "使用数量": str(u_qty),
                    "単位": u_unit,
                    "担当者": staff.strip(),
                }
                add_row(P_FILE, P_COLS, prow)
                if done:
                    idx = (df_r["原料名"] == sel_m) & (df_r["ロットNo"] == sel_lot)
                    df_r.loc[idx, "状態"] = "使用済"
                    save_df(R_FILE, df_r)
                st.success(f"紐づけ完了: {p_lot.strip()} <= {sel_m}({sel_lot})")

    st.divider()
    st.subheader("仕込み履歴一覧（セルを直接クリックして変更・行選択で削除可能）")
    df_p = load_df(P_FILE, P_COLS)
    if df_p.empty:
        st.info("仕込みデータはまだありません")
    else:
        p_cfg = {
            "使用原料": st.column_config.SelectboxColumn("使用原料", options=MATS, required=True),
            "単位": st.column_config.SelectboxColumn("単位", options=UNITS, required=True),
        }
        edited_p = st.data_editor(
            df_p,
            column_config=p_cfg,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="ed_prep",
        )
        if st.button("仕込みデータの変更を保存", type="primary"):
            save_df(P_FILE, edited_p)
            st.success("仕込みデータの変更を保存しました")
            st.rerun()

# ==========================================
# タブ3：双方向トレース検索
# ==========================================
with t3:
    df_r = load_df(R_FILE, R_COLS)
    df_p = load_df(P_FILE, P_COLS)

    if df_p.empty:
        st.info("まだ仕込み・紐づけ記録がありません")
    else:
        r
