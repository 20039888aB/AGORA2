# AgoraProf LMS - API Testing Guide

## 🚀 READY FOR FRONTEND WHEN:

✅ APIs work
✅ permissions enforced
✅ no data leaks
✅ logic centralized
✅ automation works

---

## 🔐 **ROLE-BASED TESTING**

### **SUPERADMIN** (Global Access)
```bash
# Login
POST /api/accounts/login/
{
    "email": "superadmin@example.com",
    "password": "password123"
}

# Test Superadmin Access
GET /api/accounts/users/          # Should return ALL users
GET /api/organizations/        # Should return ALL organizations
GET /api/courses/courses/       # Should return ALL courses
GET /api/enrollments/enrollments/ # Should return ALL enrollments
```

### **ADMIN** (Organization Level)
```bash
# Login
POST /api/accounts/login/
{
    "email": "admin@company1.com",
    "password": "password123"
}

# Test Admin Access
GET /api/accounts/users/          # Should return ONLY company1 users
GET /api/organizations/        # Should return ONLY company1 org
GET /api/courses/courses/       # Should return ONLY company1 courses
GET /api/enrollments/enrollments/ # Should return ONLY company1 enrollments

# Test Data Isolation (SHOULD FAIL)
GET /api/organizations/2/   # Should return 403 (different org)
GET /api/courses/courses/3/  # Should return 403 (different org)
```

### **MANAGER** (Course Instructor)
```bash
# Login
POST /api/accounts/login/
{
    "email": "manager@company1.com",
    "password": "password123"
}

# Test Manager Access
GET /api/courses/courses/       # Should return ONLY their courses
GET /api/assignments/assignments/ # Should return ONLY their assignments

# Test Permission Boundaries (SHOULD FAIL)
GET /api/accounts/users/          # Should return 403 (not admin)
GET /api/organizations/        # Should return 403 (not admin)
```

### **STUDENT** (Enrollment Access)
```bash
# Login
POST /api/accounts/login/
{
    "email": "student@company1.com",
    "password": "password123"
}

# Test Student Access
GET /api/enrollments/my_enrollments/    # Should return their enrollments
GET /api/assignments/my_submissions/    # Should return their submissions
GET /api/certificates/my_certificates/    # Should return their certificates

# Test Permission Boundaries (SHOULD FAIL)
GET /api/courses/courses/       # Should return 403 or empty (not instructor)
GET /api/assignments/assignments/ # Should return 403 (not instructor)
```

---

## 📊 **CRITICAL API ENDPOINTS TO TEST**

### **User Management**
```bash
# Create User (Admin+)
POST /api/accounts/create_user/
{
    "email": "newuser@company1.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe",
    "role": "STUDENT",
    "organization_id": "company1-uuid"
}

# Update User (Owner/Admin+)
PUT /api/accounts/users/{user_id}/
{
    "first_name": "John Updated",
    "role": "MANAGER"
}

# Get User Statistics
GET /api/accounts/statistics/
```

### **Course Management**
```bash
# Create Course (Admin+)
POST /api/courses/create_course/
{
    "title": "New Course",
    "description": "Course Description",
    "organization_id": "company1-uuid",
    "instructor_id": "manager-uuid"
}

# Publish Course (Owner/Admin+)
POST /api/courses/courses/{course_id}/publish/

# Get Course Statistics
GET /api/courses/courses/{course_id}/statistics/
```

### **Enrollment Management**
```bash
# Create Enrollment (Student)
POST /api/enrollments/create_enrollment/
{
    "course_id": "course-uuid",
    "payment_status": "COMPLETED"
}

# Update Progress (Student)
POST /api/enrollments/enrollments/{enrollment_id}/update_progress/
{
    "progress_percentage": 75.5
}

# Issue Certificate (Admin+)
POST /api/enrollments/enrollments/{enrollment_id}/issue_certificate/
```

### **Assignment Management**
```bash
# Create Assignment (Admin+)
POST /api/assignments/create_assignment/
{
    "title": "New Assignment",
    "course_id": "course-uuid",
    "assignment_type": "ESSAY"
}

# Submit Assignment (Student)
POST /api/assignments/assignment_submissions/create_submission/
{
    "assignment_id": "assignment-uuid",
    "answers": {"question1": "Answer text"}
}

# Grade Assignment (Instructor/Admin+)
POST /api/assignments/assignment_submissions/{submission_id}/grade/
{
    "score": 85.5,
    "feedback": "Good work!"
}
```

### **Certificate Management**
```bash
# Create Certificate Template (Admin+)
POST /api/certificates/templates/create_template/
{
    "name": "Default Template",
    "organization_id": "company1-uuid"
}

# Issue Certificate (Admin+)
POST /api/certificates/certificates/create_certificate/
{
    "enrollment_id": "enrollment-uuid"
}

# Verify Certificate (Public)
POST /api/certificates/public/verify_public/
{
    "verification_code": "ABC123XYZ789"
}
```

---

## 🔍 **PERMISSION TESTING CHECKLIST**

### **Data Isolation Tests**
- [ ] Admin from Org1 cannot access Org2 data
- [ ] Manager from Course1 cannot access Course2 data
- [ ] Student cannot access other students' data
- [ ] Superadmin can access all data

### **Role Boundary Tests**
- [ ] Student cannot create/modify courses
- [ ] Manager cannot manage users
- [ ] Admin cannot access other organizations
- [ ] Each role can only access their permitted endpoints

### **Business Logic Tests**
- [ ] Course capacity limits enforced
- [ ] Assignment due dates enforced
- [ ] Certificate issuance only for completed courses
- [ ] Payment status validation
- [ ] Progress calculation accuracy

---

## 🚨 **SECURITY TESTS**

### **Authentication Tests**
```bash
# Test without token
GET /api/accounts/users/          # Should return 401

# Test with invalid token
GET /api/accounts/users/          # Authorization: Bearer invalid_token
# Should return 401

# Test with expired token
GET /api/accounts/users/          # Authorization: Bearer expired_token
# Should return 401
```

### **Authorization Tests**
```bash
# Test cross-organization access
GET /api/organizations/org2-users/  # Admin from Org1 accessing Org2
# Should return 403

# Test role escalation
PUT /api/accounts/users/{user_id}/   # Student trying to change role
# Should return 403
```

### **Input Validation Tests**
```bash
# Test SQL Injection
POST /api/accounts/login/
{
    "email": "'; DROP TABLE users; --",
    "password": "password"
}
# Should return 400

# Test XSS
POST /api/courses/create_course/
{
    "title": "<script>alert('xss')</script>",
    "description": "Course description"
}
# Should sanitize/return 400
```

---

## 📈 **PERFORMANCE TESTS**

### **Load Testing**
```bash
# Test concurrent users
ab -n 100 -c 10 http://localhost:8000/api/courses/courses/

# Test large data sets
GET /api/courses/courses/?limit=1000

# Test file uploads
POST /api/assignments/assignment-files/upload_file/
# Upload 10MB file
```

---

## ✅ **SUCCESS CRITERIA**

### **API Functionality**
- [ ] All CRUD operations work correctly
- [ ] Filtering and searching works
- [ ] Pagination works
- [ ] File uploads work
- [ ] Bulk operations work

### **Permission System**
- [ ] Role-based access control enforced
- [ ] Multi-tenancy isolation works
- [ ] Object-level permissions work
- [ ] No privilege escalation possible

### **Business Logic**
- [ ] All validations enforced
- [ ] Calculations are accurate
- [ ] Workflows complete correctly
- [ ] Error handling works

### **Security**
- [ ] Authentication required for protected endpoints
- [ ] Authorization checks work
- [ ] Input validation works
- [ ] SQL injection protection works
- [ ] XSS protection works

### **Automation**
- [ ] Email notifications sent
- [ ] Audit logs created
- [ ] Certificates issued automatically
- [ ] Progress calculations work

---

## 🚀 **READY FOR FRONTEND**

When ALL above tests pass:
✅ APIs work
✅ permissions enforced  
✅ no data leaks
✅ logic centralized
✅ automation works

**THEN AND ONLY THEN** - Ready for frontend development!
