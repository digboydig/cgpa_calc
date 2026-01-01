import streamlit as st
import pandas as pd

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
    return sum(v for v in vals if v is not None)

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
    # Inputs for the CURRENTLY selected semester
    num_courses = st.number_input(
        f"Courses in Semester {current_sem}",
        min_value=1,
        max_value=12,
        value=4
    )

    course_names = [
        st.text_input(
            f"Course {i+1} name",
            f"Course {i+1}",
            key=f"course_{current_sem}_{i}"
        )
        for i in range(num_courses)
    ]

    st.markdown("---")
    st.subheader("Weights")
    same_weights = st.checkbox("Use same weights for all courses?", value=True)

    if same_weights:
        gw1 = st.number_input("EC1 (%)", 0.0, 100.0, 30.0)
        gw2 = st.number_input("EC2 (%)", 0.0, 100.0, 30.0)
        gw3 = st.number_input("EC3 (%)", 0.0, 100.0, 40.0)

        if abs(gw1 + gw2 + gw3 - 100) > 1e-6:
            st.error("Global weights must sum to 100")

    st.markdown("---")
    # Clear Data Button
    if st.button("🗑️ Clear All Data", type="primary"):
        st.session_state.semester_results = {}
        st.rerun()

# =========================================================
# Semester Tabs
# =========================================================
tabs = st.tabs([f"Semester {i}" for i in range(1, 4)])

for sem_idx, tab in enumerate(tabs, start=1):
    with tab:
        # ==========================================
        # EDIT MODE: Only if this is the selected sem
        # ==========================================
        if sem_idx == current_sem:
            st.header(f"✏️ Input: Semester {current_sem}")
            courses_data = []
            bad_weights = False

            for i, cname in enumerate(course_names):
                st.subheader(cname)

                col1, col2 = st.columns(2)
                with col1:
                    units = st.selectbox(
                        "Units",
                        [4, 5],
                        key=f"units_{current_sem}_{i}"
                    )

                with col2:
                    if calc_method == "Normalise from Class Highest":
                        unknown = st.checkbox(
                            "Class highest unknown?",
                            key=f"unk_{current_sem}_{i}"
                        )
                        if unknown:
                            h_course = st.slider(
                                "Assumed Class Highest",
                                min_value=60.0,
                                max_value=100.0,
                                value=85.0,
                                step=0.5,
                                key=f"hslider_{current_sem}_{i}"
                            )
                            st.caption("Adjust slider to see grade impact")
                        else:
                            h_course = st.number_input(
                                "Class Highest",
                                0.1, 100.0, 100.0,
                                key=f"h_{current_sem}_{i}"
                            )
                    else:
                        h_course = 100.0

                # ---------- Weights ----------
                if same_weights:
                    w1, w2, w3 = gw1, gw2, gw3
                else:
                    wc = st.columns(3)
                    w1 = wc[0].number_input("EC1 (%)", 0.0, 100.0, 30.0, key=f"w1_{current_sem}_{i}")
                    w2 = wc[1].number_input("EC2 (%)", 0.0, 100.0, 30.0, key=f"w2_{current_sem}_{i}")
                    w3 = wc[2].number_input("EC3 (%)", 0.0, 100.0, 40.0, key=f"w3_{current_sem}_{i}")

                    if abs(w1 + w2 + w3 - 100) > 1e-6:
                        st.warning("Weights must sum to 100")
                        bad_weights = True

                # ---------- EC inputs ----------
                ec_cols = st.columns(3)
                ec1 = None if ec_cols[0].checkbox("EC1 pending", key=f"p1_{current_sem}_{i}") else ec_cols[0].number_input(f"EC1 (0–{w1})", 0.0, float(w1), key=f"ec1_{current_sem}_{i}")
                ec2 = None if ec_cols[1].checkbox("EC2 pending", key=f"p2_{current_sem}_{i}") else ec_cols[1].number_input(f"EC2 (0–{w2})", 0.0, float(w2), key=f"ec2_{current_sem}_{i}")
                ec3 = None if ec_cols[2].checkbox("EC3 pending", key=f"p3_{current_sem}_{i}") else ec_cols[2].number_input(f"EC3 (0–{w3})", 0.0, float(w3), key=f"ec3_{current_sem}_{i}")

                # ---------- Projection ----------
                with st.expander("🎯 Projection (if ECs pending)"):
                    target_gp = st.selectbox("Target GP", list(GP_TO_PERCENT.keys()), index=2, key=f"tgp_{current_sem}_{i}")
                    target_percent = GP_TO_PERCENT[target_gp]
                    target_raw = (target_percent / 100) * h_course
                    current_raw = safe_sum(ec1, ec2, ec3)
                    need = target_raw - current_raw
                    pending_capacity = safe_sum(w1 if ec1 is None else 0, w2 if ec2 is None else 0, w3 if ec3 is None else 0)

                    if need <= 0:
                        st.success("Target already achievable.")
                    elif need > pending_capacity:
                        st.error("Target GP not reachable.")
                    else:
                        st.info(f"Need **{need:.2f}** more raw marks.")

                courses_data.append({
                    "Course": cname, "Units": units, "ec1": ec1, "ec2": ec2, "ec3": ec3, "h": h_course
                })
                st.divider()

            # ---------- Compute Button ----------
            if st.button("Compute Semester Result", key=f"calc_{current_sem}"):
                if bad_weights:
                    st.error("Fix weight errors before computing.")
                    st.stop()

                rows = []
                total_gp = 0
                total_units = 0

                for c in courses_data:
                    raw = safe_sum(c["ec1"], c["ec2"], c["ec3"])
                    final = (raw / c["h"]) * 100 if calc_method == "Normalise from Class Highest" else raw
                    gp, grade = grade_point_and_letter_absolute(final)
                    total_gp += gp * c["Units"]
                    total_units += c["Units"]
                    rows.append({
                        "Course": c["Course"],
                        "Units": c["Units"],
                        "Total (%)": f"{final:.2f}",
                        "GP": gp,
                        "Grade": grade,
                        "Result": "Pass" if gp >= 4.5 else "Fail"
                    })

                df = pd.DataFrame(rows)
                sgpa = total_gp / total_units if total_units else 0

                # Save to session state
                st.session_state.semester_results[current_sem] = {
                    "df": df,
                    "sgpa": sgpa,
                    "total_gp": total_gp,
                    "total_units": total_units
                }
                st.rerun()

        # ==========================================
        # VIEW MODE: Show Results if they exist
        # ==========================================
        if sem_idx in st.session_state.semester_results:
            res = st.session_state.semester_results[sem_idx]
            
            st.markdown(f"### 📄 Semester {sem_idx} Results")
            st.table(res["df"])
            
            sgpa_val = res["sgpa"]
            if sgpa_val >= 5.5:
                st.success(f"**SGPA: {sgpa_val:.2f}**")
            else:
                st.error(f"**SGPA: {sgpa_val:.2f} — FAIL**")
        else:
            if sem_idx != current_sem:
                st.info(f"Select **Semester {sem_idx}** in the sidebar to enter marks.")

# =========================================================
# Consolidated Summary & CGPA
# =========================================================
st.markdown("---")
st.header("📊 Cumulative Performance")

completed = st.session_state.semester_results

if len(completed) > 0:
    # 1. Calculate CGPA
    if len(completed) >= 2:
        cgpa = sum(v["total_gp"] for v in completed.values()) / sum(v["total_units"] for v in completed.values())
        st.success(f"## 🏆 CGPA: {cgpa:.2f}" if cgpa >= 5.5 else f"## CGPA: {cgpa:.2f} — FAIL")
        
        # Trend Chart
        trend_df = pd.DataFrame(
            {"SGPA": [completed[s]["sgpa"] for s in sorted(completed)]},
            index=[f"Semester {s}" for s in sorted(completed)]
        )
        st.line_chart(trend_df)
    else:
        st.info("CGPA will be available after completion of at least 2 semesters.")

    # 2. Consolidated Summary Table
    st.subheader("📑 Consolidated Academic Summary")
    
    all_rows = []
    for s in sorted(completed.keys()):
        # Get the dataframe for this semester
        sem_df = completed[s]["df"].copy()
        # Add a column for the Semester number
        sem_df.insert(0, "Semester", f"Sem {s}")
        all_rows.append(sem_df)
    
    if all_rows:
        full_df = pd.concat(all_rows, ignore_index=True)
        # Reorder/Clean columns if needed
        st.dataframe(full_df, use_container_width=True, hide_index=True)

        # 3. CSV Download
        csv = full_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Summary as CSV",
            data=csv,
            file_name="academic_summary.csv",
            mime="text/csv",
        )

else:
    st.write("No results computed yet.")

# =========================================================
# Footer
# =========================================================
st.markdown("---")
st.markdown("""
<div style='border:1px solid #ddd;padding:12px;border-radius:6px;background:#fff;font-size:12px;'>
<b style='color:red;'>Grade mapping:</b> A=10 | A-=9 | B=8 | B-=7 | C=6 | C-=5 | D=4 | E=2<br>
<b style='color:red;'>Pass criteria:</b> Min GP ≥ 4.5 | SGPA ≥ 5.5 | CGPA ≥ 5.5
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<p style='text-align:right; color:gray; font-size:11px;'>Developed by <b>Subodh Purohit</b> | Last updated: 01 Jan 2026</p>",
    unsafe_allow_html=True
)
