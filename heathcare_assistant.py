# Healthcare Conversation Assistant
# A modular implementation for the medical triage and symptom tracking system

import json
import datetime
import uuid
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

# ============ CORE DATA MODELS ============

class PriorityLevel(Enum):
    CRITICAL = "critical"  # Immediate medical attention needed
    URGENT = "urgent"      # Needs care within 24-48 hours
    STANDARD = "standard"  # Should be seen within 1-2 weeks
    ROUTINE = "routine"    # Regular scheduling acceptable

class Symptom:
    def __init__(self, name: str, severity: int, duration_days: int, description: str = ""):
        self.name = name
        self.severity = severity  # 1-10 scale
        self.duration_days = duration_days
        self.description = description
        self.timestamp = datetime.datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "severity": self.severity,
            "duration_days": self.duration_days,
            "description": self.description,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Symptom':
        symptom = cls(
            name=data["name"],
            severity=data["severity"],
            duration_days=data["duration_days"],
            description=data.get("description", "")
        )
        symptom.timestamp = datetime.datetime.fromisoformat(data["timestamp"])
        return symptom

class PatientProfile:
    def __init__(self, patient_id: str, name: str, age: int, gender: str):
        self.patient_id = patient_id
        self.name = name
        self.age = age
        self.gender = gender
        self.medical_history: List[str] = []
        self.allergies: List[str] = []
        self.current_medications: List[str] = []
        self.lifestyle_factors: Dict[str, Any] = {
            "smoking_status": None,
            "alcohol_consumption": None,
            "exercise_frequency": None,
            "stress_level": None
        }
    
    def to_dict(self) -> Dict:
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "medical_history": self.medical_history,
            "allergies": self.allergies,
            "current_medications": self.current_medications,
            "lifestyle_factors": self.lifestyle_factors
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PatientProfile':
        profile = cls(
            patient_id=data["patient_id"],
            name=data["name"],
            age=data["age"],
            gender=data["gender"]
        )
        profile.medical_history = data.get("medical_history", [])
        profile.allergies = data.get("allergies", [])
        profile.current_medications = data.get("current_medications", [])
        profile.lifestyle_factors = data.get("lifestyle_factors", {})
        return profile

class HealthAssessment:
    def __init__(self, patient_id: str):
        self.assessment_id = str(uuid.uuid4())
        self.patient_id = patient_id
        self.assessment_date = datetime.datetime.now()
        self.symptoms: List[Symptom] = []
        self.priority_score: int = 0  # 0-100 scale
        self.priority_level: PriorityLevel = PriorityLevel.ROUTINE
        self.recommendation: str = ""
        self.condition_predictions: List[Dict] = []  # New field for predictions
    
    def add_symptom(self, symptom: Symptom):
        self.symptoms.append(symptom)
    
    def calculate_priority(self):
        """Calculate priority based on symptoms and patient factors"""
        if not self.symptoms:
            self.priority_score = 0
            self.priority_level = PriorityLevel.ROUTINE
            return
        
        # Simple algorithm for demo purposes - would be more sophisticated in production
        base_score = 0
        
        # Factor in severity and duration
        for symptom in self.symptoms:
            symptom_score = symptom.severity * 2  # 2-20 points per symptom
            
            # Duration multiplier
            if symptom.duration_days < 2:
                duration_factor = 1.0
            elif symptom.duration_days < 7:
                duration_factor = 1.2
            elif symptom.duration_days < 30:
                duration_factor = 1.5
            else:
                duration_factor = 2.0
                
            base_score += symptom_score * duration_factor
        
        # Normalize to 0-100 scale (simple approach for demo)
        self.priority_score = min(int(base_score * 2.5), 100)
        
        # Determine priority level
        if self.priority_score >= 80:
            self.priority_level = PriorityLevel.CRITICAL
            self.recommendation = "Immediate medical attention recommended"
        elif self.priority_score >= 60:
            self.priority_level = PriorityLevel.URGENT
            self.recommendation = "Schedule appointment within 24-48 hours"
        elif self.priority_score >= 40:
            self.priority_level = PriorityLevel.STANDARD
            self.recommendation = "Schedule appointment within 1-2 weeks"
        else:
            self.priority_level = PriorityLevel.ROUTINE
            self.recommendation = "Routine appointment scheduling"
    
    def to_dict(self) -> Dict:
        return {
            "assessment_id": self.assessment_id,
            "patient_id": self.patient_id,
            "assessment_date": self.assessment_date.isoformat(),
            "symptoms": [s.to_dict() for s in self.symptoms],
            "priority_score": self.priority_score,
            "priority_level": self.priority_level.value,
            "recommendation": self.recommendation,
            "condition_predictions": self.condition_predictions  # Include predictions in dict
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'HealthAssessment':
        assessment = cls(patient_id=data["patient_id"])
        assessment.assessment_id = data["assessment_id"]
        assessment.assessment_date = datetime.datetime.fromisoformat(data["assessment_date"])
        assessment.symptoms = [Symptom.from_dict(s) for s in data["symptoms"]]
        assessment.priority_score = data["priority_score"]
        assessment.priority_level = PriorityLevel(data["priority_level"])
        assessment.recommendation = data["recommendation"]
        
        # Add predictions if available
        if "condition_predictions" in data:
            assessment.condition_predictions = data["condition_predictions"]
        else:
            assessment.condition_predictions = []
            
        return assessment
    
    
# ============ CONVERSATION MANAGER ============

class ConversationState(Enum):
    GREETING = "greeting"
    COLLECTING_SYMPTOMS = "collecting_symptoms"
    SYMPTOM_DETAILS = "symptom_details"
    MEDICAL_HISTORY = "medical_history"
    LIFESTYLE_FACTORS = "lifestyle_factors"
    SUMMARIZING = "summarizing"
    FOLLOWUP = "followup"
    COMPLETED = "completed"

class ConversationManager:
    def __init__(self, patient_id: str):
        self.patient_id = patient_id
        self.state = ConversationState.GREETING
        self.current_assessment = HealthAssessment(patient_id)
        self.current_symptom_name: Optional[str] = None
        self.conversation_history: List[Dict] = []
    
    def process_message(self, message: str) -> str:
        # Record message in conversation history
        self.conversation_history.append({
            "role": "patient",
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # Process based on current state
        response = ""
        
        if self.state == ConversationState.GREETING:
            response = self._handle_greeting(message)
        elif self.state == ConversationState.COLLECTING_SYMPTOMS:
            response = self._handle_symptom_collection(message)
        elif self.state == ConversationState.SYMPTOM_DETAILS:
            response = self._handle_symptom_details(message)
        elif self.state == ConversationState.MEDICAL_HISTORY:
            response = self._handle_medical_history(message)
        elif self.state == ConversationState.LIFESTYLE_FACTORS:
            response = self._handle_lifestyle_factors(message)
        elif self.state == ConversationState.SUMMARIZING:
            response = self._handle_summarizing(message)
        elif self.state == ConversationState.FOLLOWUP:
            response = self._handle_followup(message)
        else:
            response = "I'm not sure where we are in our conversation. Let's restart. How can I help you today?"
            self.state = ConversationState.GREETING
        
        # Record response in conversation history
        self.conversation_history.append({
            "role": "assistant",
            "message": response,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return response
    
    def _handle_greeting(self, message: str) -> str:
        # Simple greeting handler - would be more sophisticated with NLP
        self.state = ConversationState.COLLECTING_SYMPTOMS
        return ("Hello! I'm your healthcare assistant. I'd like to ask you some questions to better understand your " 
                "health concerns before connecting you with a doctor. What symptoms are you experiencing today?")
    
    def _handle_symptom_collection(self, message: str) -> str:
        # Very basic symptom extraction - would use NLP in production
        if "none" in message.lower() or "no symptoms" in message.lower():
            self.state = ConversationState.MEDICAL_HISTORY
            return ("Thank you. I understand you're not experiencing specific symptoms right now. "
                   "Let's talk about your medical history. Do you have any chronic conditions or significant past medical issues?")
        
        # Simple keyword extraction for demo
        potential_symptoms = [
            "headache", "fever", "cough", "pain", "nausea", "fatigue", 
            "dizziness", "rash", "shortness of breath", "anxiety"
        ]
        
        found_symptoms = [s for s in potential_symptoms if s in message.lower()]
        
        if not found_symptoms:
            # If no symptoms detected, ask for clarification
            return ("I want to make sure I understand your symptoms correctly. Could you please describe what you're "
                   "experiencing in simple terms? For example: headache, fever, cough, pain, etc.")
        
        # For demo, just take the first identified symptom
        self.current_symptom_name = found_symptoms[0]
        self.state = ConversationState.SYMPTOM_DETAILS
        
        return f"I understand you're experiencing {self.current_symptom_name}. On a scale of 1-10, how severe is your {self.current_symptom_name}?"
    
    def _handle_symptom_details(self, message: str) -> str:
        # Try to extract severity rating
        try:
            severity = int(''.join(filter(str.isdigit, message)))
            if not (1 <= severity <= 10):
                severity = 5  # Default to middle if out of range
        except ValueError:
            # If no number found, make an estimate based on keywords
            if any(word in message.lower() for word in ["severe", "extreme", "terrible", "worst"]):
                severity = 9
            elif any(word in message.lower() for word in ["moderate", "average", "medium"]):
                severity = 5
            elif any(word in message.lower() for word in ["mild", "slight", "little"]):
                severity = 2
            else:
                severity = 5  # Default if no severity indicators found
        
        # Now ask about duration
        return f"Thank you. How long have you been experiencing this {self.current_symptom_name}? Please specify in days if possible."
    
    def _extract_duration(self, message: str) -> int:
        # Try to extract duration in days
        words = message.lower().split()
        for i, word in enumerate(words):
            if word.isdigit() and i + 1 < len(words):
                number = int(word)
                if "day" in words[i+1] or "days" in words[i+1]:
                    return number
                elif "week" in words[i+1] or "weeks" in words[i+1]:
                    return number * 7
                elif "month" in words[i+1] or "months" in words[i+1]:
                    return number * 30
                else:
                    return number  # Assume days if no unit specified
        
        # If no number found, make an estimate based on keywords
        if any(word in message.lower() for word in ["today", "just now", "recent", "recently"]):
            return 1
        elif any(word in message.lower() for word in ["yesterday", "couple", "few"]):
            return 2
        elif "week" in message.lower():
            return 7
        elif "month" in message.lower():
            return 30
        else:
            return 3  # Default if no duration indicators found
    
    def _handle_medical_history(self, message: str) -> str:
        # In a real system, this would parse the message for medical conditions
        # For the demo, we'll just store the raw message
        
        # Move to lifestyle questions
        self.state = ConversationState.LIFESTYLE_FACTORS
        return ("Thank you for sharing your medical history. A few more questions about your lifestyle: "
               "Do you smoke, drink alcohol, or have any regular exercise routine? Also, how would you rate your stress level?")
    
    def _handle_lifestyle_factors(self, message: str) -> str:
        # In a real system, this would parse lifestyle factors
        # For the demo, we'll just record the message and move to summary
        
        # Calculate priority and prepare summary
        if self.current_symptom_name:
            # Create a symptom from the collected information
            # (In a real system, we would have collected and stored duration and severity)
            symptom = Symptom(
                name=self.current_symptom_name,
                severity=5,  # Default for demo
                duration_days=7,  # Default for demo
                description="Patient reported symptom"
            )
            self.current_assessment.add_symptom(symptom)
        
        self.current_assessment.calculate_priority()
        self.state = ConversationState.SUMMARIZING
        
        return self._generate_summary()
    
    def _generate_summary(self) -> str:
        """Generate a summary of the assessment"""
        if not self.current_assessment.symptoms:
            summary = "Based on our conversation, you didn't report any specific symptoms."
        else:
            symptoms_text = ", ".join([s.name for s in self.current_assessment.symptoms])
            summary = f"Based on our conversation, you reported: {symptoms_text}."
        
        priority = self.current_assessment.priority_level.value.capitalize()
        score = self.current_assessment.priority_score
        recommendation = self.current_assessment.recommendation
        
        return (f"{summary}\n\n"
                f"Priority: {priority} ({score}/100)\n"
                f"Recommendation: {recommendation}\n\n"
                "I'll forward this summary to the healthcare team. They'll review it and contact you about next steps. "
                "Would you like me to schedule a follow-up check-in with you in one week?")
    
    def _handle_summarizing(self, message: str) -> str:
        # Check if user wants follow-up
        if any(word in message.lower() for word in ["yes", "sure", "ok", "okay", "fine", "please"]):
            self.state = ConversationState.COMPLETED
            return ("Great! I've scheduled a follow-up conversation for one week from today. "
                   "If your condition changes before then, please don't hesitate to reach out. "
                   "Thank you for using our healthcare assistant. Take care!")
        else:
            self.state = ConversationState.COMPLETED
            return ("Thank you for using our healthcare assistant. "
                   "If your condition changes or you need further assistance, please don't hesitate to reach out. Take care!")
    
    def _handle_followup(self, message: str) -> str:
        # This would handle follow-up conversations
        # For the demo, we'll just acknowledge and close
        self.state = ConversationState.COMPLETED
        return "Thank you for the update. I'll make sure this information is added to your records."

# ============ DOCTOR INTERFACE ============

class DoctorInterface:
    def __init__(self):
        self.patient_queue: List[HealthAssessment] = []
    
    def add_assessment(self, assessment: HealthAssessment):
        """Add a new assessment to the doctor's queue"""
        self.patient_queue.append(assessment)
        # Sort queue by priority score (highest first)
        self.patient_queue.sort(key=lambda a: a.priority_score, reverse=True)
    
    def get_patient_queue(self) -> List[Dict]:
        """Get the current prioritized patient queue"""
        return [
            {
                "assessment_id": assessment.assessment_id,
                "patient_id": assessment.patient_id,
                "priority_level": assessment.priority_level.value,
                "priority_score": assessment.priority_score,
                "submission_time": assessment.assessment_date.isoformat()
            }
            for assessment in self.patient_queue
        ]
    
    def get_assessment_details(self, assessment_id: str) -> Optional[Dict]:
        """Get detailed view of a specific assessment"""
        for assessment in self.patient_queue:
            if assessment.assessment_id == assessment_id:
                return assessment.to_dict()
        return None
    
    def process_assessment(self, assessment_id: str, doctor_notes: str, schedule_appointment: bool) -> bool:
        """Process an assessment (add notes, schedule appointment, etc.)"""
        for i, assessment in enumerate(self.patient_queue):
            if assessment.assessment_id == assessment_id:
                # In a real system, would update database with doctor's decision
                # and remove from queue or mark as processed
                self.patient_queue.pop(i)
                return True
        return False

# ============ DATA STORAGE ============

class DataStorage:
    def __init__(self, storage_file: str = "healthcare_data.json"):
        self.storage_file = storage_file
        self.patients: Dict[str, PatientProfile] = {}
        self.assessments: Dict[str, HealthAssessment] = {}
        self.try_load_data()
    
    def try_load_data(self):
        """Try to load existing data from storage file"""
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
                
                # Load patient profiles
                for patient_data in data.get("patients", []):
                    patient = PatientProfile.from_dict(patient_data)
                    self.patients[patient.patient_id] = patient
                
                # Load assessments
                for assessment_data in data.get("assessments", []):
                    assessment = HealthAssessment.from_dict(assessment_data)
                    self.assessments[assessment.assessment_id] = assessment
                    
        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is invalid, start with empty data
            pass
    
    def save_data(self):
        """Save current data to storage file"""
        data = {
            "patients": [p.to_dict() for p in self.patients.values()],
            "assessments": [a.to_dict() for a in self.assessments.values()]
        }
        
        with open(self.storage_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_patient(self, patient: PatientProfile):
        """Add or update a patient profile"""
        self.patients[patient.patient_id] = patient
        self.save_data()
    
    def get_patient(self, patient_id: str) -> Optional[PatientProfile]:
        """Get a patient profile by ID"""
        return self.patients.get(patient_id)
    
    def add_assessment(self, assessment: HealthAssessment):
        """Add a new health assessment"""
        self.assessments[assessment.assessment_id] = assessment
        self.save_data()
    
    def get_assessment(self, assessment_id: str) -> Optional[HealthAssessment]:
        """Get an assessment by ID"""
        return self.assessments.get(assessment_id)
    
    def get_patient_assessments(self, patient_id: str) -> List[HealthAssessment]:
        """Get all assessments for a specific patient"""
        return [a for a in self.assessments.values() if a.patient_id == patient_id]

# ============ SAMPLE USAGE ============

def demo():
    """Demonstrate the system's functionality"""
    # Initialize storage
    storage = DataStorage()
    
    # Create a test patient
    patient_id = str(uuid.uuid4())
    patient = PatientProfile(
        patient_id=patient_id,
        name="John Doe",
        age=45,
        gender="Male"
    )
    patient.medical_history = ["Hypertension", "Type 2 Diabetes"]
    patient.allergies = ["Penicillin"]
    patient.current_medications = ["Lisinopril", "Metformin"]
    storage.add_patient(patient)
    
    # Create conversation manager
    conversation = ConversationManager(patient_id)
    
    # Simulate conversation
    responses = [
        conversation.process_message("Hello, I need medical advice"),
        conversation.process_message("I have a severe headache and some dizziness"),
        conversation.process_message("It's about an 8 out of 10"),
        conversation.process_message("It started 3 days ago"),
        conversation.process_message("I have high blood pressure and diabetes"),
        conversation.process_message("I don't smoke or drink. I try to walk daily but haven't due to the headache. My stress is high."),
        conversation.process_message("Yes, please schedule a follow-up")
    ]
    
    # Print the conversation
    for i, response in enumerate(responses):
        print(f"Assistant: {response}\n")
        if i < len(conversation.conversation_history) // 2:
            patient_msg = conversation.conversation_history[i*2]["message"]
            print(f"Patient: {patient_msg}\n")
    
    # Save the assessment
    storage.add_assessment(conversation.current_assessment)
    
    # Create doctor interface and add the assessment
    doctor_interface = DoctorInterface()
    doctor_interface.add_assessment(conversation.current_assessment)
    
    # Print the doctor's queue
    print("\nDoctor's Patient Queue:")
    for i, patient in enumerate(doctor_interface.get_patient_queue()):
        print(f"{i+1}. Priority: {patient['priority_level']} ({patient['priority_score']}/100)")
    
    # Print assessment details
    assessment_id = conversation.current_assessment.assessment_id
    details = doctor_interface.get_assessment_details(assessment_id)
    print("\nAssessment Details:")
    print(f"Priority: {details['priority_level']} ({details['priority_score']}/100)")
    print(f"Recommendation: {details['recommendation']}")
    print("Symptoms:")
    for symptom in details['symptoms']:
        print(f"- {symptom['name']}: Severity {symptom['severity']}/10, Duration: {symptom['duration_days']} days")

if __name__ == "__main__":
    demo()