## Vision-Based Hole Detection & Automation System

This project presents an end-to-end vision-based inspection system designed for detecting holes in mechanical components and integrating the results with an industrial automation workflow.

The system uses computer vision techniques to identify circular features, compute their coordinates, convert them into real-world units through calibration, and transmit the data to a PLC for robotic operations.

A web-based control dashboard is developed to manage and execute different modules of the system, including camera calibration, live monitoring, hole detection, and PLC communication.

### 🔧 Key Features
- Real-time hole detection using OpenCV (Hough Circle Transform)
- Pixel-to-real-world coordinate calibration
- Integration with Siemens PLC for automation
- Web-based UI for system control and monitoring
- Modular pipeline for vision processing and execution

### 🧠 System Workflow
Camera → Image Processing → Hole Detection → Coordinate Extraction → Calibration → PLC Communication → Robot Action

### 💻 Tech Stack
- Python
- OpenCV
- Flask (Backend UI)
- HTML/CSS (Frontend UI)
- Snap7 (PLC Communication)

### 📊 Performance
- Repeatability:  
  - X-axis: ±0.11 mm  
  - Y-axis: ±0.13 mm  

### 📸 Outputs
The system successfully detects multiple holes, extracts coordinates, and transmits them for automation tasks through a structured pipeline.

---

This project demonstrates the integration of computer vision, web-based interfaces, and industrial automation systems into a unified inspection solution.
