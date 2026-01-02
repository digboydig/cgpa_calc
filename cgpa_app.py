import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="🎓 SGPA / CGPA Calculator", layout="centered")

# =========================================================
# Helper functions
# =========================================================
def grade_point_and_letter_absolute(total):
    if total >= 90: return 10, "A"
    elif total >= 80: return 9, "A-"
    elif total >= 70: return 8, "B"
    elif total >= 60: return 7, "B-"
    elif total >= 50: return 6, "C"
    elif total >= 45: return 5, "C-"
    elif total >= 35: return 4, "D"
    else: return 2, "E"

GP_TO_PERCENT = {10: 90, 9: 80, 8: 70, 7: 60, 6: 50, 5: 45, 4: 35, 2: 0}

def safe_sum(*vals):
    return sum(v for v in vals if pd.notna(v))

# ---------- Styling helpers (NEW, UI ONLY) ----------
def style_grade(val):
    colors = {
        "A": "#2ecc71", "A-": "#2ecc71",
        "B": "#27ae60", "B-": "#27ae60",
        "C": "#f1c40f", "C-": "#f1c40f",
        "D": "#e67e22",
        "E": "#e74c3c",
    }
    return f"color:{colors.get(val, 'black')}; font-weight:bold;"

def style_result(val):
    return (
        "color:green;font-weight:bold;"
        if "PASS" in val
        else "color:red;font-weight:bold;"
    )

# =========================================================
# Session state
# =========================================================
if "semester_results" not in st.session_state:
    st.session_state.semester_results = {}

# =========================================================
# Title
# =========================================================
st.title("🎓 SGPA / CGPA Calculator")
st.caption("Semester-wise SGPA with normalisation, projections & CGPA")

# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.header("Semester Selection")
    current_sem = st.selectbox(
        "Select semester to Edit",
        [1, 2, 3],
        format_func=lambda x: f"Semester {x}"
    )

    st.markdown("---")
    calc_method = st.radio(
        "Calculation Method",
        ["Direct Average", "Normalise from Class Highest"]
    )

    st.markdown("---")
    num_courses = st.number_input(
        f"Courses in Semester {current_sem}",
        min_value=1,
        max_value=15,
        value=4
    )

    st.info("💡 Tip: Enter course names and marks directly in the table.")

    st.markdown("---")
    st.subheader("Weights")
    same_weights = st.checkbox("Use same weights for all courses?", value=True)

    gw1, gw2, gw3 = 30.0, 30.0, 40.0

    if same_weights:
        gw1 = st.number_input("EC1 (%)", 0.0, 100.0, 30.0)
        gw2 = st.number_input("EC2 (%)", 0.0, 100.0, 30.0)
        gw3 = st.number_input("EC3 (%)", 0.0, 100.0, 40.0)

        if abs(gw1 + gw2 + gw3 - 100) > 1e-6:
            st.error("Global weights must sum to 100")

    st.markdown("---")
    if st.button("🗑️ Clear All Data", type="primary"):
        st.session_state.semester_results = {}
        st.rerun()

# =========================================================
# Semester Tabs
# =========================================================
tabs = st.tabs([f"Semester {i}" for i in range(1, 4)])

for sem_idx, tab in enumerate(tabs, start=1):
    with tab:

        if sem_idx == current_sem:
            st.header(f"Input: Semester {current_sem} Marks")

            default_data = {
                "Course Name": [f"Course {i+1}" for i in range(num_courses)],
                "Units": [4] * num_courses,
                "EC1": [None] * num_courses,
                "EC2": [None] * num_courses,
                "EC3": [None] * num_courses,
            }

            if not same_weights:
                default_data["W1"] = [30.0] * num_courses
                default_data["W2"] = [30.0] * num_courses
                default_data["W3"] = [40.0] * num_courses

            if calc_method == "Normalise from Class Highest":
                default_data["Highest"] = [100.0] * num_courses

            df_template = pd.DataFrame(default_data)

            df_template["Units"] = df_template["Units"].astype("category")
            df_template["Units"] = df_template["Units"].cat.set_categories([4, 5])

            numeric_cols = ["EC1", "EC2", "EC3"]
            if "Highest" in df_template.columns:
                numeric_cols.append("Highest")
            if "W1" in df_template.columns:
                numeric_cols.extend(["W1", "W2", "W3"])

            for col in numeric_cols:
                df_template[col] = df_template[col].astype("float64")

            editor_kwargs = {
                "data": df_template,
                "use_container_width": True,
                "key": f"editor_{current_sem}",
                "num_rows": "dynamic"
            }

            try:
                edited_df = st.data_editor(**editor_kwargs)
            except AttributeError:
                try:
                    edited_df = st.experimental_data_editor(**editor_kwargs)
                except Exception:
                    del editor_kwargs["num_rows"]
                    edited_df = st.experimental_data_editor(**editor_kwargs)
            except TypeError:
                del editor_kwargs["num_rows"]
                edited_df = st.data_editor(**editor_kwargs)

            # =====================================================
            # Grade Projection Tool (UNCHANGED)
            # =====================================================
            st.markdown("#### 🎯 Grade Projection Tool")
            with st.expander("Calculate required marks for a specific course"):
                course_opts = edited_df["Course Name"].unique().tolist()
                if course_opts:
                    selected_course = st.selectbox("Select Course", course_opts)
                    subset = edited_df[edited_df["Course Name"] == selected_course]

                    if not subset.empty:
                        row = subset.iloc[0]

                        if same_weights:
                            p_w1, p_w2, p_w3 = gw1, gw2, gw3
                        else:
                            p_w1 = row.get("W1", 30.0)
                            p_w2 = row.get("W2", 30.0)
                            p_w3 = row.get("W3", 40.0)

                        p_h = row.get("Highest", 100.0) if calc_method == "Normalise from Class Highest" else 100.0

                        p_ec1 = row.get("EC1")
                        p_ec2 = row.get("EC2")
                        p_ec3 = row.get("EC3")

                        current_raw = safe_sum(p_ec1, p_ec2, p_ec3)

                        target_gp = st.selectbox("Target GP", list(GP_TO_PERCENT.keys()), index=2)
                        target_percent = GP_TO_PERCENT[target_gp]
                        target_raw = (target_percent / 100) * p_h

                        need = target_raw - current_raw

                        pending_capacity = 0
                        if pd.isna(p_ec1): pending_capacity += p_w1
                        if pd.isna(p_ec2): pending_capacity += p_w2
                        if pd.isna(p_ec3): pending_capacity += p_w3

                        col1, col2 = st.columns(2)
                        col1.metric("Current Raw Score", f"{current_raw:.2f}")
                        col2.metric("Required Raw Score", f"{target_raw:.2f}")

                        if need <= 0:
                            st.success(f"✅ Target {target_gp} already achieved!")
                        elif need > pending_capacity:
                            st.error(f"❌ Cannot reach {target_gp}.")
                        else:
                            st.info(f"You need **{need:.2f}** more marks.")

            st.divider()

            # =====================================================
            # Compute Semester Result
            # =====================================================
            if st.button("Compute Semester Result", key=f"calc_{current_sem}"):
                rows = []
                total_gp = 0
                total_units = 0

                for _, row in edited_df.iterrows():
                    cname = row["Course Name"]
                    units = row["Units"] if pd.notna(row["Units"]) else 4

                    ec1 = row.get("EC1", 0)
                    ec2 = row.get("EC2", 0)
                    ec3 = row.get("EC3", 0)

                    absolute_total = safe_sum(ec1, ec2, ec3)

                    h_course = row.get("Highest", 100.0) if calc_method == "Normalise from Class Highest" else 100.0
                    if h_course <= 0:
                        h_course = 100.0

                    final = (absolute_total / h_course) * 100
                    gp, grade = grade_point_and_letter_absolute(final)

                    total_gp += gp * units
                    total_units += units

                    rows.append({
                        "Course": cname,
                        "Units": units,
                        "Total Marks (Absolute)": f"{absolute_total:.2f}",
                        "Total % (Normalised)": f"{final:.2f}",
                        "GP": gp,
                        "Grade": grade,
                        "Result": "✅ PASS" if gp >= 5 else "❌ FAIL"
                    })

                st.session_state.semester_results[current_sem] = {
                    "df": pd.DataFrame(rows),
                    "sgpa": total_gp / total_units if total_units else 0,
                    "total_gp": total_gp,
                    "total_units": total_units
                }
                st.rerun()

        if sem_idx in st.session_state.semester_results:
            res = st.session_state.semester_results[sem_idx]
            st.markdown(f"### 📄 Semester {sem_idx} Results")

            styled_df = (
                res["df"]
                .style
                .applymap(style_grade, subset=["Grade"])
                .applymap(style_result, subset=["Result"])
            )

            st.dataframe(styled_df, use_container_width=True)

            sgpa_val = res["sgpa"]
            if sgpa_val >= 5.5:
                st.success(f"**SGPA: {sgpa_val:.2f}**")
            elif sgpa_val >= 5.0:
                st.warning(f"**SGPA: {sgpa_val:.2f} — BORDERLINE**")
            else:
                st.error(f"**SGPA: {sgpa_val:.2f} — FAIL**")

        elif sem_idx != current_sem:
            st.info(f"Select **Semester {sem_idx}** in the sidebar to enter marks.")

# =========================================================
# CGPA
# =========================================================
st.markdown("---")
st.header("📊 Cumulative Performance")

completed = st.session_state.semester_results

if len(completed) >= 2:
    cgpa = sum(v["total_gp"] for v in completed.values()) / sum(v["total_units"] for v in completed.values())

    if cgpa >= 5.5:
        st.success(f"## 🏆 CGPA: {cgpa:.2f}")
    elif cgpa >= 5.0:
        st.warning(f"## CGPA: {cgpa:.2f} — BORDERLINE")
    else:
        st.error(f"## CGPA: {cgpa:.2f} — FAIL 😢")

    chart_data = pd.DataFrame({
        "Semester": [f"Semester {s}" for s in sorted(completed)],
        "SGPA": [completed[s]["sgpa"] for s in sorted(completed)]
    })

    chart = alt.Chart(chart_data).mark_bar(
        size=50,
        cornerRadiusTopLeft=6,
        cornerRadiusTopRight=6
    ).encode(
        x=alt.X("Semester", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("SGPA", scale=alt.Scale(domain=[0, 10])),
        tooltip=["Semester", "SGPA"]
    ).properties(title="SGPA Trend")

    st.altair_chart(chart, use_container_width=True)

elif len(completed) > 0:
    st.info("CGPA will be available after completion of at least 2 semesters.")

# =========================================================
# Consolidated Summary Table (UNCHANGED)
# =========================================================
st.markdown("---")
st.subheader("📑 Consolidated Academic Summary")

all_rows = []
for s in sorted(completed.keys()):
    sem_df = completed[s]["df"].copy()
    sem_df.insert(0, "Semester", f"Sem {s}")
    all_rows.append(sem_df)

if all_rows:
    full_df = pd.concat(all_rows, ignore_index=True)

    styled_full = (
        full_df
        .style
        .applymap(style_grade, subset=["Grade"])
        .applymap(style_result, subset=["Result"])
    )

    st.dataframe(styled_full.set_index(["Semester", "Course"]), use_container_width=True)

    csv = full_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Consolidated Summary (CSV)",
        data=csv,
        file_name="academic_summary.csv",
        mime="text/csv",
    )
else:
    st.info("No semester results available yet.")

# =========================================================
# FULL ORIGINAL FOOTER (PRESERVED)
# =========================================================
st.markdown("---")
st.markdown("""
<div style='border:1px solid #ddd;padding:12px;border-radius:6px;background:#fff;font-size:12px;'>
<b style='color:red;'>Grade mapping:</b> A=10 | A-=9 | B=8 | B-=7 | C=6 | C-=5 | D=4 | E=2<br>
<b style='color:red;'>Pass criteria:</b> Min GP ≥ 5 | SGPA ≥ 5.5 | CGPA ≥ 5.5<br>
<b style='color:red;'>Legend:</b> EC1 = Assignment/Quiz | EC2 = Mid Semester Exam | EC3 = Comprehensive Examination
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<p style='text-align:right; color:gray; font-size:11px;'>Developed by <b>Subodh Purohit</b> | Last updated: 1 Jan 2026</p>",
    unsafe_allow_html=True
)
