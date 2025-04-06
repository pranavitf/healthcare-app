# app.py - Updated Flask web application with ChatGPT integration
# Add these imports at the top of the file

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import json
import uuid
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Import from our healthcare modules
from healthcare_assistant import (
    PatientProfile, HealthAssessment, ConversationManager, 
    DoctorInterface, DataStorage, PriorityLevel, Symptom
)

# Import the new ChatGPT integration
from chatgpt_integration import ChatGPTManager, integrate_with_health_assessment

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_hackathon')

# Initialize our data storage
storage = DataStorage()
doctor_interface = DoctorInterface()

# Initialize ChatGPT API with your key
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_ORG_ID = os.environ.get('OPENAI_ORG_ID', '')

# Load any existing assessments into the doctor's queue
for assessment in storage.assessments.values():
    doctor_interface.add_assessment(assessment)

# Simple user authentication (for demo purposes only)
users = {
    "doctor": {
        "password": generate_password_hash("doctor123"),
        "role": "doctor"
    },
    "patient": {
        "password": generate_password_hash("patient123"),
        "role": "patient"
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in users and check_password_hash(users[username]['password'], password):
            session['username'] = username
            session['role'] = users[username]['role']
            
            if users[username]['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_chat'))
        
        return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('patient_id', None)
    session.pop('chatgpt_session', None)
    return redirect(url_for('index'))

@app.route('/patient/chat')
def patient_chat():
    if 'username' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))
    
    # For demo, assign a patient ID if none exists
    if 'patient_id' not in session:
        # Check if we have a profile for this username
        existing_patients = [p for p in storage.patients.values() if p.name == session['username']]
        
        if existing_patients:
            session['patient_id'] = existing_patients[0].patient_id
        else:
            # Create a new patient profile
            patient_id = str(uuid.uuid4())
            patient = PatientProfile(
                patient_id=patient_id,
                name=session['username'],
                age=35,  # Default for demo
                gender="Not specified"  # Default for demo
            )
            storage.add_patient(patient)
            session['patient_id'] = patient_id
    
    return render_template('patient_chat.html')

@app.route('/api/patient/message', methods=['POST'])
def patient_message():
    if 'username' not in session or session['role'] != 'patient' or 'patient_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    message = data.get('message', '')
    
    # Initialize or retrieve ChatGPT conversation history
    if 'conversation_history' not in session:
        # Create a new ChatGPT manager
        chatgpt_manager = ChatGPTManager(OPENAI_API_KEY, OPENAI_ORG_ID)
        session['conversation_history'] = json.dumps(chatgpt_manager.conversation_history)
        
        # Create a new assessment
        health_assessment = HealthAssessment(session['patient_id'])
        session['assessment_id'] = health_assessment.assessment_id
        
        # Initial welcome message
        response = "Hello! I'm your healthcare assistant. I'd like to understand your health concerns today. Could you please describe what symptoms or issues you're experiencing?"
    else:
        try:
            # Restore conversation history
            conversation_history = json.loads(session['conversation_history'])
            
            # Create ChatGPT manager with existing history
            chatgpt_manager = ChatGPTManager(OPENAI_API_KEY, OPENAI_ORG_ID)
            chatgpt_manager.conversation_history = conversation_history
            
            # Process message through ChatGPT
            response = chatgpt_manager.process_message(message)
            
            # Save updated conversation history
            session['conversation_history'] = json.dumps(chatgpt_manager.conversation_history)
            
            # Count meaningful exchanges (ignore very short responses)
            meaningful_exchanges = 0
            for i, msg in enumerate(chatgpt_manager.conversation_history):
                if msg["role"] == "user" and len(msg["content"]) > 5:
                    meaningful_exchanges += 1
            
            # Ensure we gather enough information before concluding
            # Only conclude after at least 5 meaningful exchanges or if user explicitly asks
            if (meaningful_exchanges >= 5 and len(chatgpt_manager.conversation_history) >= 10) or \
               "end conversation" in message.lower() or \
               "what is your diagnosis" in message.lower() or \
               "show me the summary" in message.lower():
                
                # Get the assessment to update
                health_assessment = HealthAssessment(session['patient_id'])
                if 'assessment_id' in session:
                    health_assessment.assessment_id = session['assessment_id']
                
                # Fill assessment with data from ChatGPT
                integrate_with_health_assessment(chatgpt_manager, health_assessment, storage)
                
                # Save the assessment
                storage.add_assessment(health_assessment)
                doctor_interface.add_assessment(health_assessment)
                
                # Add concluding message
                response = "Thank you for providing all this information. Based on what you've shared, I've created a summary for our healthcare team. They'll review it and contact you about next steps for your care."
                
                # Clear session
                session.pop('conversation_history', None)
                session.pop('assessment_id', None)
                
                # Set flag to indicate completion
                return jsonify({
                    "response": response,
                    "conversation_completed": True
                })
                
        except Exception as e:
            print(f"Error processing message: {e}")
            response = "I apologize, but I'm having trouble processing your message right now. Could you please try again?"
    
    return jsonify({
        "response": response,
        "conversation_completed": False
    })

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    
    return render_template('doctor_dashboard.html')

@app.route('/api/doctor/queue')
def doctor_queue():
    if 'username' not in session or session['role'] != 'doctor':
        return jsonify({"error": "Unauthorized"}), 401
    
    queue = doctor_interface.get_patient_queue()
    
    # Enhance queue data with patient names
    for item in queue:
        patient = storage.get_patient(item['patient_id'])
        if patient:
            item['patient_name'] = patient.name
        else:
            item['patient_name'] = "Unknown Patient"
    
    return jsonify(queue)

@app.route('/api/doctor/assessment/<assessment_id>')
def get_assessment(assessment_id):
    if 'username' not in session or session['role'] != 'doctor':
        return jsonify({"error": "Unauthorized"}), 401
    
    details = doctor_interface.get_assessment_details(assessment_id)
    
    if not details:
        return jsonify({"error": "Assessment not found"}), 404
    
    # Add patient information
    patient = storage.get_patient(details['patient_id'])
    if patient:
        details['patient'] = patient.to_dict()
    
    return jsonify(details)

@app.route('/api/doctor/process', methods=['POST'])
def process_assessment():
    if 'username' not in session or session['role'] != 'doctor':
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    assessment_id = data.get('assessment_id')
    doctor_notes = data.get('notes', '')
    schedule_appointment = data.get('schedule_appointment', False)
    
    success = doctor_interface.process_assessment(
        assessment_id=assessment_id,
        doctor_notes=doctor_notes,
        schedule_appointment=schedule_appointment
    )
    
    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Assessment not found"}), 404

@app.route('/api/doctor/followups')
def get_followups():
    if 'username' not in session or session['role'] != 'doctor':
        return jsonify({"error": "Unauthorized"}), 401
    
    # In a real system, would query for scheduled follow-ups
    # For demo, just return an empty list
    return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)