# ReachGenie Partnership Application - Frontend Implementation Guide

This guide provides detailed instructions for implementing the frontend portion of the ReachGenie Partnership Application system, including API endpoints, request formats, and expected responses.

## 1. Submit Partnership Application (Public Endpoint)

This is the main endpoint used by potential partners to submit their application form.

### API Endpoint
```
POST /api/partner-applications
```

### Request Format
```javascript
// Example fetch request
const response = await fetch('/api/partner-applications', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    company_name: "Acme Corporation",
    contact_name: "John Doe",
    contact_email: "john.doe@acmecorp.com",
    contact_phone: "+1 555-123-4567",
    website: "https://www.acmecorp.com",
    partnership_type: "RESELLER", // Options: "RESELLER", "REFERRAL", "TECHNOLOGY"
    company_size: "11-50", // Options: "1-10", "11-50", "51-200", "201-500", "501+"
    industry: "Technology",
    current_solutions: "Currently using CRM system X and marketing automation Y",
    target_market: "Small and medium businesses in the finance sector",
    motivation: "Looking to expand our product offerings with AI-powered solutions",
    additional_information: "Our team has 5 years of experience in the CRM space"
  })
});

const data = await response.json();
```

### Response Format (Success - 201 Created)
```javascript
{
  "id": "123e4567-e89b-12d3-a456-426614174000", // UUID of the created application
  "message": "Your partnership application has been submitted successfully. We will contact you soon."
}
```

### Response Format (Error - 422 Unprocessable Entity)
```javascript
{
  "detail": [
    {
      "loc": ["body", "company_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## 2. Form Field Requirements

### Required Fields
- `company_name` (string)
- `contact_name` (string)
- `contact_email` (valid email)
- `partnership_type` (enum: "RESELLER", "REFERRAL", "TECHNOLOGY")
- `company_size` (enum: "1-10", "11-50", "51-200", "201-500", "501+")
- `industry` (string)
- `motivation` (string)

### Optional Fields
- `contact_phone` (string)
- `website` (string)
- `current_solutions` (string)
- `target_market` (string)
- `additional_information` (string)

## 3. Frontend Implementation Example

### React Component Example
```jsx
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';

const PartnershipApplicationForm = () => {
  const { register, handleSubmit, formState: { errors } } = useForm();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  
  const onSubmit = async (data) => {
    setIsSubmitting(true);
    try {
      const response = await fetch('/api/partner-applications', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setSubmitResult({
          success: true,
          message: result.message,
          id: result.id
        });
      } else {
        setSubmitResult({
          success: false,
          message: "Failed to submit application. Please try again.",
          errors: result.detail
        });
      }
    } catch (error) {
      setSubmitResult({
        success: false,
        message: "An error occurred. Please try again later."
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h1 className="text-2xl font-bold mb-6">ReachGenie Partnership Application</h1>
      
      {submitResult?.success ? (
        <div className="p-4 bg-green-50 border border-green-200 rounded-md mb-6">
          <h2 className="text-lg font-semibold text-green-800">Application Submitted Successfully!</h2>
          <p className="text-green-700 mt-1">{submitResult.message}</p>
          <p className="text-sm text-green-600 mt-4">
            We'll send a confirmation email to your provided email address.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Company Information */}
          <div>
            <h2 className="text-xl font-semibold mb-3">Company Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Company Name *</label>
                <input
                  type="text"
                  {...register('company_name', { required: true })}
                  className="w-full p-2 border rounded-md"
                />
                {errors.company_name && <span className="text-red-500 text-sm">Required field</span>}
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Industry *</label>
                <input
                  type="text"
                  {...register('industry', { required: true })}
                  className="w-full p-2 border rounded-md"
                />
                {errors.industry && <span className="text-red-500 text-sm">Required field</span>}
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Website</label>
                <input
                  type="url"
                  {...register('website')}
                  className="w-full p-2 border rounded-md"
                  placeholder="https://"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Company Size *</label>
                <select
                  {...register('company_size', { required: true })}
                  className="w-full p-2 border rounded-md"
                >
                  <option value="">Select company size</option>
                  <option value="1-10">1-10 employees</option>
                  <option value="11-50">11-50 employees</option>
                  <option value="51-200">51-200 employees</option>
                  <option value="201-500">201-500 employees</option>
                  <option value="501+">501+ employees</option>
                </select>
                {errors.company_size && <span className="text-red-500 text-sm">Required field</span>}
              </div>
            </div>
          </div>
          
          {/* Contact Information */}
          <div>
            <h2 className="text-xl font-semibold mb-3">Contact Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Contact Name *</label>
                <input
                  type="text"
                  {...register('contact_name', { required: true })}
                  className="w-full p-2 border rounded-md"
                />
                {errors.contact_name && <span className="text-red-500 text-sm">Required field</span>}
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Contact Email *</label>
                <input
                  type="email"
                  {...register('contact_email', {
                    required: true,
                    pattern: /^\S+@\S+\.\S+$/
                  })}
                  className="w-full p-2 border rounded-md"
                />
                {errors.contact_email && <span className="text-red-500 text-sm">Valid email required</span>}
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Contact Phone</label>
                <input
                  type="text"
                  {...register('contact_phone')}
                  className="w-full p-2 border rounded-md"
                />
              </div>
            </div>
          </div>
          
          {/* Partnership Details */}
          <div>
            <h2 className="text-xl font-semibold mb-3">Partnership Details</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Partnership Type *</label>
                <select
                  {...register('partnership_type', { required: true })}
                  className="w-full p-2 border rounded-md"
                >
                  <option value="">Select partnership type</option>
                  <option value="RESELLER">Reseller</option>
                  <option value="REFERRAL">Referral</option>
                  <option value="TECHNOLOGY">Technology</option>
                </select>
                {errors.partnership_type && <span className="text-red-500 text-sm">Required field</span>}
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Current Solutions</label>
                <textarea
                  {...register('current_solutions')}
                  className="w-full p-2 border rounded-md"
                  rows="2"
                  placeholder="What solutions are you currently using?"
                ></textarea>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Target Market</label>
                <textarea
                  {...register('target_market')}
                  className="w-full p-2 border rounded-md"
                  rows="2"
                  placeholder="Who are your primary customers?"
                ></textarea>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Partnership Motivation *</label>
                <textarea
                  {...register('motivation', { required: true })}
                  className="w-full p-2 border rounded-md"
                  rows="3"
                  placeholder="Why are you interested in partnering with ReachGenie?"
                ></textarea>
                {errors.motivation && <span className="text-red-500 text-sm">Required field</span>}
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Additional Information</label>
                <textarea
                  {...register('additional_information')}
                  className="w-full p-2 border rounded-md"
                  rows="3"
                  placeholder="Any other information you'd like to share?"
                ></textarea>
              </div>
            </div>
          </div>
          
          {submitResult?.success === false && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-700">{submitResult.message}</p>
            </div>
          )}
          
          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md disabled:opacity-50"
            >
              {isSubmitting ? 'Submitting...' : 'Submit Application'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default PartnershipApplicationForm;
```

## 4. Success Flow and Customer Experience

1. The user fills out the partnership application form
2. On submission, the form data is sent to the `/api/partner-applications` endpoint
3. The backend processes the application, stores it, and sends a personalized confirmation email with:
   - Customized greeting with the contact's name
   - References to their company and industry (researched via Perplexity API)
   - Information specific to their partnership type
   - 3 personalized sales tips relevant to their business
   - Next steps and follow-up timeline
   - Professional signature from Qudsia Piracha, Director of Product

4. The user receives a success message in the UI
5. Shortly after, they receive the personalized confirmation email in their inbox

## 5. Backend Email Process

The backend automatically sends a highly personalized acknowledgment email to the applicant:

1. **Sender Information**:
   - From: Qudsia Piracha <qudsia@workhub.ai>
   - CC: ashaheen@workhub.ai

2. **Email Content**:
   - Professional HTML formatting with proper styling
   - Company-specific information from Perplexity API research
   - Partnership-specific details
   - 3 personalized sales tips for their specific business
   - Clear next steps and timeline

3. **Signature**:
   ```
   Qudsia Piracha
   Director of Product
   ReachGenie 
   https://reachgenie.leanai.ventures
   ```

## 6. Best Practices for Implementation

1. **Form Validation**:
   - Implement thorough client-side validation before submission
   - Validate email format, required fields, and field lengths
   - Show validation errors inline next to the relevant fields

2. **Error Handling**:
   - Display meaningful error messages for API failures
   - Log errors for debugging purposes
   - Provide users with clear next steps if something goes wrong

3. **Loading States**:
   - Show loading indicators during submission
   - Disable form controls during submission to prevent double-submits
   - Provide visual feedback during the API call

4. **Success State**:
   - Display a clear success message after submission
   - Remove the form to prevent duplicate submissions
   - Provide clear expectations about what happens next

5. **Responsive Design**:
   - Ensure the form works well on all device sizes
   - Test on mobile, tablet, and desktop viewports
   - Adjust layout for smaller screens

6. **Accessibility**:
   - Make the form accessible to all users
   - Include proper labels for screen readers
   - Ensure keyboard navigation works correctly
   - Test with screen readers and keyboard-only navigation
   - Maintain WCAG 2.1 AA compliance

7. **Performance**:
   - Optimize component rendering
   - Implement form state management efficiently
   - Avoid unnecessary re-renders

## 7. Testing Checklist

- [ ] All required fields show validation errors when empty
- [ ] Email validation works correctly
- [ ] Form submission shows loading state
- [ ] Success message appears after successful submission
- [ ] Error handling works for API failures
- [ ] Responsive layout works on all device sizes
- [ ] Accessibility testing with screen readers
- [ ] Keyboard navigation works correctly
- [ ] Form can't be submitted multiple times 