// MongoDB initialization script for EchoSafe
// This script runs when MongoDB container starts for the first time

// Switch to echosafe database
db = db.getSiblingDB('echosafe');

// Create collections with validation
db.createCollection('hr_users', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["username", "password_hash", "created_at"],
      properties: {
        username: {
          bsonType: "string",
          minLength: 3,
          maxLength: 50,
          description: "HR username - must be unique"
        },
        password_hash: {
          bsonType: "string",
          description: "Bcrypt hash of password"
        },
        created_at: {
          bsonType: "date",
          description: "Account creation timestamp"
        },
        role: {
          bsonType: "string",
          enum: ["admin", "investigator"],
          description: "User role"
        },
        is_active: {
          bsonType: "bool",
          description: "Account status"
        }
      }
    }
  }
});

db.createCollection('reports', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["case_id", "report_text", "urgency_score", "status", "created_at"],
      properties: {
        case_id: {
          bsonType: "string",
          minLength: 8,
          description: "Unique case identifier"
        },
        report_text: {
          bsonType: "string",
          minLength: 10,
          maxLength: 5000,
          description: "Report content"
        },
        urgency_score: {
          bsonType: "number",
          minimum: 0,
          maximum: 1,
          description: "AI-calculated urgency score"
        },
        status: {
          bsonType: "string",
          enum: ["pending", "investigating", "resolved"],
          description: "Case status"
        },
        created_at: {
          bsonType: "date",
          description: "Report submission timestamp"
        },
        updated_at: {
          bsonType: "date",
          description: "Last update timestamp"
        },
        updated_by: {
          bsonType: "string",
          description: "HR user who last updated the case"
        },
        submitted_via: {
          bsonType: "string",
          enum: ["api", "web"],
          description: "Submission method"
        }
      }
    }
  }
});

// Create indexes for performance
db.hr_users.createIndex({ "username": 1 }, { unique: true });
db.hr_users.createIndex({ "created_at": -1 });
db.hr_users.createIndex({ "is_active": 1 });

db.reports.createIndex({ "case_id": 1 }, { unique: true });
db.reports.createIndex({ "urgency_score": -1 });
db.reports.createIndex({ "created_at": -1 });
db.reports.createIndex({ "status": 1, "created_at": -1 });
db.reports.createIndex({ "updated_at": -1 });

// Create text index for search functionality
db.reports.createIndex({ 
  "case_id": "text", 
  "report_text": "text" 
}, {
  weights: {
    "case_id": 10,
    "report_text": 1
  }
});

print('EchoSafe database initialized successfully');
print('Collections: hr_users, reports');
print('Indexes created for optimal performance');
