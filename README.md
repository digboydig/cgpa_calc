🎓 SGPA / CGPA Calculator 

A clean, interactive Streamlit web app to calculate course-wise grades, SGPA, CGPA, and estimate required marks for pending components.
Supports both absolute and relative grading, customizable weightages, and an integrated projection tool.
✨ Features
🧮 Per-course or global weightage (EC1/EC2/EC3 must sum to 100)
🎯 Absolute & Relative grading with adjustable cutoffs
📊 Projection tool – estimate how much you need to score in pending components
🟢 Color-coded results (green = pass, red = fail)
💾 Download results (CSV) and Reset instantly
📘 Footer info with grade mapping and pass criteria
⚙️ Setup
# 1. Install dependencies
pip install streamlit pandas numpy


🧠 Grade Mapping (Absolute)
Grade	Point	Range (%)
A	10	≥ 90
A-	9	80–89
B	8	70–79
B-	7	60–69
C	6	50–59
C-	5	45–49
D	4	35–44
E	2	< 35
Pass criteria:
≥ 4.5 per course
CGPA ≥ 5.5 overall
💡 Projection Example
If EC3 is pending, select it and enter your target grade (e.g., 8 or 9) —
the app tells you how much you need in the remaining components to reach that goal.

🧑‍💻 Author: SP
Developed with ❤️ using Streamlit, Pandas, and NumPy.
