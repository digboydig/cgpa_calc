import streamlit as st
import pandas as pd

st.set_page_config(page_title="🎓 SGPA / CGPA Calculator", layout="centered")

# -------------------------
# Helper functions
# -------------------------
def grade_point_and_letter_absolute(total):
    if total >= 90: return 10, "A"
    elif total >= 80: return 9, "A-"
    elif total >= 70: return 8, "B"
    elif total >= 60: return 7, "B-"
    elif total >= 50: return 6, "C"
    elif total >= 45: return 5, "C-"
    elif total >= 35: return 4, "D"
    else: return 2, "E"

def total_percent_from_components(m1, m2, m3):
    return (m1 or 0) + (m2 or 0) + (m3 or 0)

# -------------------------
# Session State
# -------------------------
if "semester_results" not in st.session_state:
    st.session_state.semester_results = {}

# -------------------------
# Title
# -------------------------
st.title("🎓 SGPA / CGPA Calculator")
st.caption("Semester-wise SGPA with automatic CGPA calculation")

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.header("Semester Selection")
    current_sem = st.selectbox(
        "Select semester",
        [1, 2, 3],
        format_func=lambda x: f"Semester {x}"
    )

    st.markdown("---")
    num_courses = st.number_input("Courses in this semester", 1, 12, 4)

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
    w1 = st.number_input("EC1 (%)", 0.0, 100.0, 30.0)
    w2 = st.number_input("EC2 (%)", 0.0, 100.0, 30.0)
    w3 = st.number_input("EC3 (%)", 0.0, 100.0, 40.0)

    if abs(w1 + w2 + w3 - 100) > 1e-6:
        st.error("Weights must sum to 100")

# -------------------------
# Tabs (All semesters)
# -------------------------
tabs = st.tabs([f"Semester {i}" for i in range(1, 4)])

for sem_idx, tab in enumerate(tabs, start=1):
    with tab:
        if sem_idx != current_sem:
            st.info("Select this semester from sidebar to edit.")
            continue

        st.subheader(f"📚 Semester {current_sem}")
        courses_data = []

        for i, cname in enumerate(course_names):
            st.markdown(f"### {cname}")

            col1, col2 = st.columns(2)
            with col1:
                units = st.selectbox("Units", [4, 5], key=f"units_{current_sem}_{i}")
            with col2:
                h_course = st.number_input(
                    "Class Highest",
                    0.1, 100.0, 100.0,
                    key=f"h_{current_sem}_{i}"
                )

            ec = st.columns(3)
            ec1 = ec[0].number_input(f"EC1 (0–{w1})", 0.0, w1, key=f"ec1_{current_sem}_{i}")
            ec2 = ec[1].number_input(f"EC2 (0–{w2})", 0.0, w2, key=f"ec2_{current_sem}_{i}")
            ec3 = ec[2].number_input(f"EC3 (0–{w3})", 0.0, w3, key=f"ec3_{current_sem}_{i}")

            courses_data.append({
                "Course": cname,
                "Units": units,
                "ec1": ec1,
                "ec2": ec2,
                "ec3": ec3,
                "h": h_course
            })

            st.divider()

        # -------------------------
        # Compute Semester SGPA
        # -------------------------
        if st.button("Compute Semester Result", key=f"calc_{current_sem}"):
            rows = []
            total_gp = 0
            total_units = 0

            for c in courses_data:
                raw = total_percent_from_components(c["ec1"], c["ec2"], c["ec3"])
                final = (raw / c["h"]) * 100

                gp, grade = grade_point_and_letter_absolute(final)
                credit_pts = gp * c["Units"]

                total_gp += credit_pts
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

            st.session_state.semester_results[current_sem] = {
                "df": df,
                "sgpa": sgpa,
                "total_gp": total_gp,
                "total_units": total_units
            }

            st.table(df)

            if sgpa >= 5.5:
                st.success(f"Semester SGPA: {sgpa:.2f} — PASS")
            else:
                st.error(f"Semester SGPA: {sgpa:.2f} — FAIL")

# -------------------------
# CGPA + Analytics
# -------------------------
st.markdown("---")
st.header("📊 Cumulative Performance")

completed = st.session_state.semester_results

if len(completed) >= 2:
    total_gp_all = sum(v["total_gp"] for v in completed.values())
    total_units_all = sum(v["total_units"] for v in completed.values())
    cgpa = total_gp_all / total_units_all

    if cgpa >= 5.5:
        st.success(f"CGPA: {cgpa:.2f} — PASS")
    else:
        st.error(f"CGPA: {cgpa:.2f} — FAIL")

    # SGPA Trend Chart (Streamlit-native)
    trend_df = pd.DataFrame({
        "Semester": sorted(completed.keys()),
        "SGPA": [completed[s]["sgpa"] for s in sorted(completed.keys())]
    }).set_index("Semester")

    st.subheader("SGPA Trend")
    st.line_chart(trend_df)

else:
    st.info("CGPA will be available after completion of at least 2 semesters.")

# -------------------------
# Exports
# -------------------------
st.markdown("---")
st.header("📥 Export Results")

if completed:
    for sem, data in completed.items():
        csv = data["df"].to_csv(index=False).encode("utf-8")
        st.download_button(
            f"Download Semester {sem} CSV",
            csv,
            file_name=f"semester_{sem}_results.csv",
            mime="text/csv"
        )

    # Full transcript
    transcript = pd.concat(
        [data["df"].assign(Semester=sem) for sem, data in completed.items()],
        ignore_index=True
    )

    st.download_button(
        "Download Full Transcript (CSV)",
        transcript.to_csv(index=False).encode("utf-8"),
        file_name="full_transcript.csv",
        mime="text/csv"
    )

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.caption("GP ≥ 4.5 per course | SGPA / CGPA ≥ 5.5 to clear")

st.markdown(
    "<p style='text-align:right; color:gray; font-size:11px;'>Developed by <b>Subodh Purohit</b></p>",
    unsafe_allow_html=True
)
