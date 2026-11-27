import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

st.set_page_config(page_title="トレーサビリティ", layout="wide")
JST = ZoneInfo("Asia/Tokyo")
RF = "raw_materials.csv"
PF = "production_batches.csv"
MATS = ["小麦粉", "液卵", "イースト", "乳化剤", "全粒粉"]
UNITS = ["kg", "g", "L", "mL", "袋", "箱", "本"]
RC = ["受入日時", "原料名", "ロットNo", "仕入先", "受入数量", "単位", "賞味期限", "状態"]
PC = ["仕込み日時", "製品名", "製造ロットNo", "使用原料", "原料ロットNo", "使用数量", "単位", "担当者"]


def load_df(p, c):
    if os.path.exists(p):
        df = pd.read_csv(p, dtype=str)
        if list(df.columns) == c:
            return df.fillna("")
    return pd.DataFrame(columns=c)


def save_df(p, df):
    df.to_csv(p, index=False, encoding="utf-8-sig")


st.title("トレーサビリティ")
t1, t2, t3 = st.tabs(["1.原料受入", "2.仕込み紐づけ", "3.双方向トレース"])

with t1:
    with st.form("f1", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        m = c1.selectbox("原料名", MATS)
        s = c1.text_input("仕入先")
        lot = c2.text_input("原料ロットNo")
        exp = c2.date_input("賞味期限", value=datetime.now(JST).date())
        qty = c3.number_input("数量", min_value=0.1, value=25.0, step=0.5)
        u = c3.selectbox("単位", UNITS)
        ok1 = st.form_submit_button("受入登録", type="primary")

    if ok1:
        if not lot.strip():
            st.error("ロットNoを入力してください")
        else:
            now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
            row = {"受入日時": now, "原料名": m, "ロットNo": lot.strip(), "仕入先": s.strip(), "受入数量": str(qty), "単位": u, "賞味期限": str(exp), "状態": "使用中"}
            save_df(RF, pd.concat([load_df(RF, RC), pd.DataFrame([row])], ignore_index=True))
            st.success(f"登録完了: {m} ({lot.strip()})")

    st.subheader("受入一覧（直接編集・削除可）")
    df_r = load_df(RF, RC)
    if not df_r.empty:
        cfg_r = {"原料名": st.column_config.SelectboxColumn(options=MATS), "単位": st.column_config.SelectboxColumn(options=UNITS), "状態": st.column_config.SelectboxColumn(options=["使用中", "使用済"])}
        ed_r = st.data_editor(df_r, column_config=cfg_r, num_rows="dynamic", use_container_width=True, hide_index=True, key="er")
        if st.button("受入の変更を保存", type="primary"):
            save_df(RF, ed_r)
            st.rerun()

with t2:
    df_r = load_df(RF, RC)
    act = df_r[df_r["状態"] == "使用中"]
    c1, c2 = st.columns(2)
    sm = c1.selectbox("1.原料名", MATS)
    sub = act[act["原料名"] == sm]
    slot = c2.selectbox("2.原料ロットNo", sub["ロットNo"].tolist()) if not sub.empty else None
    if sub.empty:
        c2.warning("在庫ロットなし")

    if slot:
        with st.form("f2", clear_on_submit=True):
            p1, p2, p3 = st.columns(3)
            prod = p1.text_input("製品名")
            plot = p1.text_input("製造ロットNo", value=f"PRD-{datetime.now(JST).strftime('%Y%m%d')}-01")
            uq = p2.number_input("使用量", min_value=0.1, value=10.0, step=0.5)
            uu = p2.selectbox("単位", UNITS)
            stf = p3.text_input("担当者")
            done = p3.checkbox("使い切りにする")
            ok2 = st.form_submit_button("紐づけ登録", type="primary")

        if ok2:
            if not prod.strip() or not plot.strip():
                st.error("製品名と製造ロットNoを入力してください")
            else:
                now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
                prow = {"仕込み日時": now, "製品名": prod.strip(), "製造ロットNo": plot.strip(), "使用原料": sm, "原料ロットNo": slot, "使用数量": str(uq), "単位": uu, "担当者": stf.strip()}
                save_df(PF, pd.concat([load_df(PF, PC), pd.DataFrame([prow])], ignore_index=True))
                if done:
                    df_r.loc[(df_r["原料名"] == sm) & (df_r["ロットNo"] == slot), "状態"] = "使用済"
                    save_df(RF, df_r)
                st.success(f"登録完了: {plot.strip()} <= {sm}({slot})")

    st.subheader("仕込み一覧（直接編集・削除可）")
    df_p = load_df(PF, PC)
    if not df_p.empty:
        cfg_p = {"使用原料": st.column_config.SelectboxColumn(options=MATS), "単位": st.column_config.SelectboxColumn(options=UNITS)}
        ed_p = st.data_editor(df_p, column_config=cfg_p, num_rows="dynamic", use_container_width=True, hide_index=True, key="ep")
        if st.button("仕込みの変更を保存", type="primary"):
            save_df(PF, ed_p)
            st.rerun()

with t3:
    df_r = load_df(RF, RC)[["原料名", "ロットNo", "仕入先", "賞味期限"]].drop_duplicates(["原料名", "ロットNo"])
    df_p = load_df(PF, PC)
    if df_p.empty:
        st.info("記録がありません")
    else:
        mg = pd.merge(df_p, df_r, left_on=["使用原料", "原料ロットNo"], right_on=["原料名", "ロットNo"], how="left").drop(columns=["原料名", "ロットNo"])
        mode = st.radio("追跡方向", ["トレースバック（製品→原料）", "トレースフォワード（原料→製品）"], horizontal=True)
        if "バック" in mode:
            c1, c2 = st.columns(2)
            sp = c1.selectbox("製造ロットNo", ["すべて"] + sorted(mg["製造ロットNo"].unique().tolist()))
            kp = c2.text_input("製品名・ロット検索")
            res = mg[mg["製造ロットNo"] == sp] if sp != "すべて" else mg
            if kp.strip():
                res = res[res["製造ロットNo"].str.contains(kp.strip(), na=False) | res["製品名"].str.contains(kp.strip(), na=False)]
            fname = "traceback.csv"
        else:
            c1, c2, c3 = st.columns(3)
            sf = c1.selectbox("原料名", ["すべて"] + MATS)
            sub = mg if sf == "すべて" else mg[mg["使用原料"] == sf]
            sr = c2.selectbox("原料ロットNo", ["すべて"] + sorted(sub["原料ロットNo"].unique().tolist()))
            kr = c3.text_input("原料ロット検索")
            res = sub[sub["原料ロットNo"] == sr] if sr != "すべて" else sub
            if kr.strip():
                res = res[res["原料ロットNo"].str.contains(kr.strip(), na=False)]
            fname = "traceforward.csv"

        st.dataframe(res, use_container_width=True, hide_index=True)
        csv = res.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV出力", csv, fname, "text/csv")
