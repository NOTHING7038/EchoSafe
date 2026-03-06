"""
EchoSafe AI Model Training Script
Trains a keyword-based urgency classification model for report triage
"""

import json
import pickle

# Training data
training_data = [
    {"text": "There is a threat to my safety", "urgency": 0.95},
    {"text": "Physical violence occurred today", "urgency": 0.95},
    {"text": "Emergency situation immediate help needed", "urgency": 0.9},
    {"text": "Dangerous behavior in workplace", "urgency": 0.85},
    {"text": "Someone threatened me with violence", "urgency": 0.9},
    {"text": "Harassment continues daily", "urgency": 0.65},
    {"text": "Discrimination in hiring process", "urgency": 0.6},
    {"text": "Inappropriate comments from manager", "urgency": 0.55},
    {"text": "Conflict with coworker ongoing", "urgency": 0.5},
    {"text": "Unfair treatment at work", "urgency": 0.45},
    {"text": "Minor issue needs attention", "urgency": 0.3},
    {"text": "Small scheduling problem", "urgency": 0.25},
    {"text": "General feedback about policies", "urgency": 0.2},
    {"text": "Suggestion for improvement", "urgency": 0.15},
    {"text": "Administrative question", "urgency": 0.1},
]

# Keyword-based urgency model
urgency_model = {
    "high_priority_keywords": {
        "threat": 0.95, "physical": 0.9, "violence": 0.95, "emergency": 0.9,
        "immediate": 0.85, "danger": 0.85, "attack": 0.95, "weapon": 0.95,
        "hurt": 0.9, "killed": 0.95
    },
    "medium_priority_keywords": {
        "harassment": 0.65, "discrimination": 0.6, "inappropriate": 0.55,
        "conflict": 0.5, "unfair": 0.45, "complaint": 0.5, "issue": 0.4, "problem": 0.35
    },
    "low_priority_keywords": {
        "minor": 0.3, "small": 0.25, "feedback": 0.2, "suggestion": 0.15,
        "admin": 0.1, "question": 0.1
    }
}

def train_model():
    """Train the urgency scoring model"""
    print("\n" + "=" * 70)
    print("ECHOSAFE AI MODEL TRAINING")
    print("=" * 70)
    
    print("\nDataset Summary:")
    print(f"  Training samples: {len(training_data)}")
    print(f"  High urgency (>0.7): {sum(1 for d in training_data if d['urgency'] > 0.7)}")
    print(f"  Medium urgency (0.4-0.7): {sum(1 for d in training_data if 0.4 <= d['urgency'] <= 0.7)}")
    print(f"  Low urgency (<0.4): {sum(1 for d in training_data if d['urgency'] < 0.4)}")
    
    print("\nKeyword-Based Model:")
    print(f"  High priority keywords: {len(urgency_model['high_priority_keywords'])}")
    print(f"  Medium priority keywords: {len(urgency_model['medium_priority_keywords'])}")
    print(f"  Low priority keywords: {len(urgency_model['low_priority_keywords'])}")
    
    print("\nModel Performance (on training data):")
    correct = 0
    for sample in training_data:
        text = sample['text'].lower()
        expected = sample['urgency']
        predicted = 0.3
        
        for keyword, score in urgency_model['high_priority_keywords'].items():
            if keyword in text:
                predicted = max(predicted, score)
        for keyword, score in urgency_model['medium_priority_keywords'].items():
            if keyword in text:
                predicted = max(predicted, score)
        for keyword, score in urgency_model['low_priority_keywords'].items():
            if keyword in text:
                predicted = max(predicted, score)
        
        if abs(predicted - expected) <= 0.15:
            correct += 1
    
    accuracy = (correct / len(training_data)) * 100
    print(f"  Accuracy: {accuracy:.1f}%")
    print(f"  Correct predictions: {correct}/{len(training_data)}")
    
    # Save models
    print("\nSaving model artifacts...")
    with open('urgency_model.pkl', 'wb') as f:
        pickle.dump(urgency_model, f)
    print("  Saved: urgency_model.pkl")
    
    with open('training_data.json', 'w') as f:
        json.dump(training_data, f, indent=2)
    print("  Saved: training_data.json")
    
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)
    print("\nModel Information:")
    print("  Type: Keyword-based urgency classifier")
    print("  Input: Report text (string)")
    print("  Output: Urgency score (0.0-1.0)")
    print("  Methodology: Keyword matching with priority weighting")
    print("\nIntegration:")
    print("  The backend app.py uses score_urgency() function")
    print("  Reports are automatically scored and sorted by urgency")
    print("\nFuture Enhancement:")
    print("  Replace with TensorFlow NLP for sentiment analysis")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    train_model()
