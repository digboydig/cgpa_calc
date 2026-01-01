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
    # Treat None or NaN as 0 for summing
    return sum(v for v in vals if pd.notna(v))

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
    # Number of courses controls the initial rows in the table
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

    # Global weights variables
    gw1, gw2, gw3 = 30.0, 30.0, 40.0
    
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
            st.header(f"Input: Semester {current_sem} Marks")
            
            # 1. Prepare Initial Data for the Editor
            default_data = {
                "Course Name": [f"Course {i+1}" for i in range(num_courses)],
                "Units": [4] * num_courses,
                "EC1": [None] * num_courses,
                "EC2": [None] * num_courses,
                "EC3": [None] * num_courses,
            }
            
            # Add Weight columns if not same_weights
            if not same_weights:
                default_data["W1"] = [30.0] * num_courses
                default_data["W2"] = [30.0] * num_courses
                default_data["W3"] = [40.0] * num_courses
                
            # Add Highest column if Normalisation is ON
            if calc_method == "Normalise from Class Highest":
                default_data["Highest"] = [100.0] * num_courses

            df_template = pd.DataFrame(default_data)

            # --- COMPATIBILITY FIX: FORCE CATEGORICAL FOR DROPDOWN ---
            # Instead of st.column_config, we use pandas types to enforce the dropdown
            df_template["Units"] = df_template["Units"].astype("category")
            # We explicitly set the categories we want to appear in the dropdown
            df_template["Units"] = df_template["Units"].cat.set_categories([4, 5])
            
            # Ensure numeric columns are floats (prevents text input errors)
            numeric_cols = ["EC1", "EC2", "EC3"]
            if "Highest" in df_template.columns: numeric_cols.append("Highest")
            if "W1" in df_template.columns: numeric_cols.extend(["W1", "W2", "W3"])
            
            for col in numeric_cols:
                df_template[col] = df_template[col].astype("float64")

            # 3. Render Data Editor (Check for version compatibility)
            editor_kwargs = {
                "data": df_template,
                "use_container_width": True,
                "key": f"editor_{current_sem}",
                "num_rows": "dynamic" # This allows adding/deleting rows
            }

            try:
                # Try standard data_editor
                edited_df = st.data_editor(**editor_kwargs)
            except AttributeError:
                # Fallback to experimental_data_editor for older Streamlit versions
                try:
                    edited_df = st.experimental_data_editor(**editor_kwargs)
                except Exception:
                    # Fallback for very old versions (remove num_rows if that fails)
                    del editor_kwargs["num_rows"]
                    if hasattr(st, "experimental_data_editor"):
                        edited_df = st.experimental_data_editor(**editor_kwargs)
                    else:
                        st.error("Your Streamlit version is too old to support the Table Editor. Please upgrade.")
                        st.stop()
            except TypeError:
                # If num_rows is not supported in the installed version
                del editor_kwargs["num_rows"]
                edited_df = st.data_editor(**editor_kwargs)

            
            # 4. Projection Tool
            st.markdown("#### 🎯 Grade Projection Tool")
            with st.expander("Calculate required marks for a specific course"):
                course_opts = edited_df["Course Name"].unique().tolist()
                if course_opts:
                    selected_course = st.selectbox("Select Course", course_opts)
                    # Get data for this course
                    # Handle potential empty dataframe or missing selection
                    subset = edited_df[edited_df["Course Name"] == selected_course]
                    
                    if not subset.empty:
                        row = subset.iloc[0]
                        
                        # Determine Weights
                        if same_weights:
                            p_w1, p_w2, p_w3 = gw1, gw2, gw3
                        else:
                            p_w1 = row.get("W1", 30.0)
                            p_w2 = row.get("W2", 30.0)
                            p_w3 = row.get("W3", 40.0)

                        # Determine Highest
                        p_h = row.get("Highest", 100.0) if calc_method == "Normalise from Class Highest" else 100.0
                        
                        # Inputs
                        p_ec1 = row.get("EC1")
                        p_ec2 = row.get("EC2")
                        p_ec3 = row.get("EC3")
                        
                        current_raw = safe_sum(p_ec1, p_ec2, p_ec3)
                        
                        target_gp = st.selectbox("Target GP", list(GP_TO_PERCENT.keys()), index=2)
                        target_percent = GP_TO_PERCENT[target_gp]
                        target_raw = (target_percent / 100) * p_h
                        
                        need = target_raw - current_raw
                        
                        # Calculate capacity of pending components
                        pending_capacity = 0
                        if pd.isna(p_ec1): pending_capacity += p_w1
                        if pd.isna(p_ec2): pending_capacity += p_w2
                        if pd.isna(p_ec3): pending_capacity += p_w3
                        
                        col_proj1, col_proj2 = st.columns(2)
                        col_proj1.metric("Current Raw Score", f"{current_raw:.2f}")
                        col_proj2.metric("Required Raw Score", f"{target_raw:.2f}")
                        
                        if need <= 0:
                            st.success(f"✅ Target {target_gp} already achieved!")
                        elif need > pending_capacity:
                            st.error(f"❌ Cannot reach {target_gp}. Max possible addition is {pending_capacity:.2f}.")
                        else:
                            st.info(f"You need **{need:.2f}** more marks from pending components.")

            st.divider()

            # 5. Compute Button
            if st.button("Compute Semester Result", key=f"calc_{current_sem}"):
                rows = []
                total_gp = 0
                total_units = 0
                
                # Check Global Weights if applicable
                if same_weights and abs(gw1 + gw2 + gw3 - 100) > 1e-6:
                    st.error("Global weights must sum to 100.")
                    st.stop()

                for index, row in edited_df.iterrows():
                    cname = row["Course Name"]
                    # Handle units being potentially NaN if user cleared it, default to 4
                    units = row["Units"]
                    if pd.isna(units): units = 4
                    
                    # Weights validation (if per course)
                    if not same_weights:
                        w1 = row.get("W1", 0)
                        w2 = row.get("W2", 0)
                        w3 = row.get("W3", 0)
                        # Ensure we handle NaNs in weights
                        w1 = 0 if pd.isna(w1) else w1
                        w2 = 0 if pd.isna(w2) else w2
                        w3 = 0 if pd.isna(w3) else w3
                        
                        if abs(w1 + w2 + w3 - 100) > 1e-6:
                            st.error(f"Weights for '{cname}' must sum to 100.")
                            st.stop()
                    
                    # Marks
                    ec1 = row.get("EC1", 0)
                    ec2 = row.get("EC2", 0)
                    ec3 = row.get("EC3", 0)
                    raw = safe_sum(ec1, ec2, ec3)
                    
                    # Highest
                    h_course = row.get("Highest", 100.0) if calc_method == "Normalise from Class Highest" else 100.0
                    if pd.isna(h_course) or h_course <= 0: h_course = 100.0
                    
                    final = (raw / h_course) * 100
                    gp, grade = grade_point_and_letter_absolute(final)
                    
                    total_gp += gp * units
                    total_units += units
                    
                    rows.append({
                        "Course": cname,
                        "Units": units,
                        "Total (%)": f"{final:.2f}",
                        "GP": gp,
                        "Grade": grade,
                        "Result": "Pass" if gp >= 4.5 else "Fail"
                    })

                result_df = pd.DataFrame(rows)
                sgpa = total_gp / total_units if total_units else 0

                # Save to session state
                st.session_state.semester_results[current_sem] = {
                    "df": result_df,
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
        
        # Trend Chart (Bar Graph with Altair)
        chart_data = pd.DataFrame({
            "Semester": [f"Semester {s}" for s in sorted(completed)],
            "SGPA": [completed[s]["sgpa"] for s in sorted(completed)]
        })

        c = alt.Chart(chart_data).mark_bar(
            size=50,
            cornerRadiusTopLeft=6,
            cornerRadiusTopRight=6,
            color="#4F8BF9"
        ).encode(
            x=alt.X('Semester', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('SGPA', scale=alt.Scale(domain=[0, 10])),
            tooltip=['Semester', 'SGPA']
        ).properties(
            title="SGPA Trend"
        )
        st.altair_chart(c, use_container_width=True)
    else:
        st.info("CGPA will be available after completion of at least 2 semesters.")

    # 2. Consolidated Summary Table
    st.subheader("📑 Consolidated Academic Summary")
    
    all_rows = []
    for s in sorted(completed.keys()):
        sem_df = completed[s]["df"].copy()
        sem_df.insert(0, "Semester", f"Sem {s}")
        all_rows.append(sem_df)
    
    if all_rows:
        full_df = pd.concat(all_rows, ignore_index=True)
        # Use st.table with MultiIndex for merged look
        st.table(full_df.set_index(["Semester", "Course"]))

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
<b style='color:red;'>Pass criteria:</b> Min GP ≥ 4.5 | SGPA ≥ 5.5 | CGPA ≥ 5.5<br>
<b style='color:red;'>Legend:</b> EC1 = Assignment/Quiz | EC2 = Mid Semester Exam | EC3 = Comprehensive Examination
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<p style='text-align:right; color:gray; font-size:11px;'>Developed by <b>Subodh Purohit</b> | Last updated: 1 Jan 2026</p>",
    unsafe_allow_html=True
)
