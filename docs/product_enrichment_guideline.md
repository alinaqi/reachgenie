# Product Enrichment Feature: Frontend Implementation Guide

## Overview

We've enhanced the product creation endpoint to support additional fields and automatic enrichment via Perplexity API. This guide explains how to update your frontend to work with these new capabilities.

## New Product Fields

The updated product endpoint now supports the following fields:

1. **product_name** (required): Name of the product
2. **description** (optional): Detailed description of the product
3. **product_url** (optional): URL to the product's website
4. **file** (optional): Documentation file for the product (PDF, DOCX, TXT)

When a product URL is provided, the backend will automatically use Perplexity API to enrich the product with additional information.

## API Endpoint Changes

The endpoint remains the same but now accepts additional form fields:

```
POST /api/companies/{company_id}/products
```

### Request Format

Use `multipart/form-data` format with the following fields:

```javascript
const formData = new FormData();
formData.append('product_name', productName);
formData.append('description', description); // Optional
formData.append('product_url', productUrl);  // Optional
if (file) {
  formData.append('file', file);            // Optional
}
```

### Response Format

The response includes the new fields:

```json
{
  "id": "uuid-string",
  "company_id": "company-uuid-string",
  "product_name": "Product Name",
  "description": "Product description...",
  "product_url": "https://example.com/product",
  "file_name": "uuid-filename.pdf",
  "original_filename": "original-filename.pdf",
  "enriched_information": {
    "overview": "Product overview...",
    "key_value_proposition": "Key value proposition...",
    "pricing": "Pricing information...",
    "reviews": ["Review 1", "Review 2", "Review 3"],
    "market_overview": "Market overview...",
    "competitors": "List of competitors..."
  },
  "created_at": "2023-01-01T00:00:00Z",
  "deleted": false
}
```

## Implementation Guidelines

### 1. Update Product Creation Form

Add new form fields for the additional product information:

```jsx
// React component example
const ProductForm = () => {
  const [productName, setProductName] = useState('');
  const [description, setDescription] = useState('');
  const [productUrl, setProductUrl] = useState('');
  const [file, setFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    const formData = new FormData();
    formData.append('product_name', productName);
    
    if (description) {
      formData.append('description', description);
    }
    
    if (productUrl) {
      formData.append('product_url', productUrl);
    }
    
    if (file) {
      formData.append('file', file);
    }
    
    try {
      const response = await axios.post(
        `/api/companies/${companyId}/products`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      
      // Handle success
      console.log('Product created:', response.data);
      // Redirect or show success message
    } catch (error) {
      // Handle error
      console.error('Error creating product:', error);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">
          Product Name*
        </label>
        <input
          type="text"
          value={productName}
          onChange={(e) => setProductName(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          required
        />
      </div>
      
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          rows={4}
        />
      </div>
      
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">
          Product URL
        </label>
        <input
          type="url"
          value={productUrl}
          onChange={(e) => setProductUrl(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          placeholder="https://example.com/product"
        />
        <p className="mt-1 text-sm text-gray-500">
          Adding a URL will automatically enrich your product with additional information
        </p>
      </div>
      
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">
          Documentation
        </label>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
          className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
          accept=".pdf,.docx,.txt"
        />
        <p className="mt-1 text-sm text-gray-500">
          Accepted formats: PDF, DOCX, TXT
        </p>
      </div>
      
      <button
        type="submit"
        className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        disabled={isSubmitting}
      >
        {isSubmitting ? (
          <>
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Creating Product...
          </>
        ) : (
          'Create Product'
        )}
      </button>
    </form>
  );
};
```

### 2. Display Enriched Information

Create a component to display the enriched information:

```jsx
const EnrichedProductInfo = ({ enrichedInfo }) => {
  if (!enrichedInfo) return null;
  
  return (
    <div className="bg-gray-50 p-4 rounded-lg mt-4">
      <h3 className="text-lg font-medium text-gray-900 mb-2">Product Information</h3>
      
      {enrichedInfo.overview && (
        <div className="mb-3">
          <h4 className="text-sm font-medium text-gray-700">Overview</h4>
          <p className="text-sm text-gray-600">{enrichedInfo.overview}</p>
        </div>
      )}
      
      {enrichedInfo.key_value_proposition && (
        <div className="mb-3">
          <h4 className="text-sm font-medium text-gray-700">Key Value Proposition</h4>
          <p className="text-sm text-gray-600">{enrichedInfo.key_value_proposition}</p>
        </div>
      )}
      
      {enrichedInfo.pricing && (
        <div className="mb-3">
          <h4 className="text-sm font-medium text-gray-700">Pricing</h4>
          <p className="text-sm text-gray-600">{enrichedInfo.pricing}</p>
        </div>
      )}
      
      {enrichedInfo.reviews && enrichedInfo.reviews.length > 0 && (
        <div className="mb-3">
          <h4 className="text-sm font-medium text-gray-700">Reviews</h4>
          <ul className="list-disc pl-5 text-sm text-gray-600">
            {enrichedInfo.reviews.map((review, index) => (
              <li key={index}>{review}</li>
            ))}
          </ul>
        </div>
      )}
      
      {enrichedInfo.market_overview && (
        <div className="mb-3">
          <h4 className="text-sm font-medium text-gray-700">Market Overview</h4>
          <p className="text-sm text-gray-600">{enrichedInfo.market_overview}</p>
        </div>
      )}
      
      {enrichedInfo.competitors && (
        <div className="mb-3">
          <h4 className="text-sm font-medium text-gray-700">Competitors</h4>
          <p className="text-sm text-gray-600">{enrichedInfo.competitors}</p>
        </div>
      )}
    </div>
  );
};
```

### 3. Update Product Detail View

Enhance your product detail view to show the new fields:

```jsx
const ProductDetail = ({ product }) => {
  return (
    <div className="bg-white shadow overflow-hidden sm:rounded-lg">
      <div className="px-4 py-5 sm:px-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900">
          {product.product_name}
        </h3>
        {product.product_url && (
          <p className="mt-1 max-w-2xl text-sm text-gray-500">
            <a 
              href={product.product_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-indigo-600 hover:text-indigo-900"
            >
              Visit Product Website
            </a>
          </p>
        )}
      </div>
      
      <div className="border-t border-gray-200">
        <dl>
          {product.description && (
            <>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Description</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {product.description}
                </dd>
              </div>
            </>
          )}
          
          {product.original_filename && (
            <>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Documentation</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  <a 
                    href={`/api/files/${product.file_name}`} 
                    className="text-indigo-600 hover:text-indigo-900"
                    target="_blank" 
                    rel="noopener noreferrer"
                  >
                    {product.original_filename}
                  </a>
                </dd>
              </div>
            </>
          )}
        </dl>
      </div>
      
      {product.enriched_information && (
        <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
          <EnrichedProductInfo enrichedInfo={product.enriched_information} />
        </div>
      )}
    </div>
  );
};
```

### 4. Update Product Edit Form

When editing a product, make sure to include the new fields:

```jsx
const ProductEditForm = ({ product, onSubmit }) => {
  const [productName, setProductName] = useState(product.product_name);
  const [description, setDescription] = useState(product.description || '');
  const [productUrl, setProductUrl] = useState(product.product_url || '');
  const [file, setFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    const formData = new FormData();
    formData.append('product_name', productName);
    
    if (description) {
      formData.append('description', description);
    }
    
    if (productUrl) {
      formData.append('product_url', productUrl);
    }
    
    if (file) {
      formData.append('file', file);
    }
    
    try {
      await onSubmit(formData);
    } catch (error) {
      console.error('Error updating product:', error);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Form JSX similar to the create form, but with pre-filled values
  // ...
};
```

## Enrichment Process

When a product URL is provided, the backend will:

1. Make a request to the Perplexity API with the company name and product URL
2. Extract detailed information about the product
3. Store this information in the `enriched_information` field
4. Return the enriched product data in the response

The enriched information includes:

- **Overview**: General description of the product
- **Key Value Proposition**: Main selling points
- **Pricing**: Pricing information if available
- **Reviews**: Up to 3 good reviews
- **Market Overview**: Information about the market
- **Competitors**: List of competitors

## Best Practices

### 1. User Experience

- **Inform users about enrichment**: Add a tooltip or info message explaining that adding a URL will trigger automatic enrichment
- **Show loading states**: Display a loading indicator during form submission, especially when enrichment is happening
- **Provide feedback**: Let users know if enrichment was successful or failed

### 2. URL Handling

- **Validate URLs**: Ensure the URL is properly formatted before submission
- **Normalize URLs**: Add "https://" prefix if missing
- **Handle errors**: Provide clear error messages if the URL is invalid or unreachable

### 3. File Handling

- **Validate file types**: Only allow PDF, DOCX, and TXT files
- **Show file size limits**: Inform users about any file size restrictions
- **Preview files**: If possible, provide a preview of the uploaded file

### 4. Mobile Responsiveness

- **Optimize for small screens**: Ensure the form and enriched information display properly on mobile devices
- **Simplify on mobile**: Consider a more compact view of enriched information on smaller screens

### 5. Error Handling

- **Graceful degradation**: If enrichment fails, still allow the product to be created with the provided information
- **Retry options**: Allow users to retry enrichment if it fails
- **Clear error messages**: Provide specific error messages for different failure scenarios

## Example Implementation Timeline

1. Update product creation form with new fields (1-2 days)
2. Add loading states and user guidance (1 day)
3. Implement product detail view with enriched information display (1-2 days)
4. Add product editing capability for the new fields (1 day)
5. Test thoroughly across devices and browsers (1-2 days)

## Technical Considerations

### 1. State Management

If using Redux or another state management library, update your product slice/store to include the new fields:

```javascript
// Example Redux slice update
const productSlice = createSlice({
  name: 'products',
  initialState: {
    items: [],
    loading: false,
    error: null,
  },
  reducers: {
    // Update reducers to handle new fields
  },
  extraReducers: (builder) => {
    // Handle async actions
  },
});
```

### 2. TypeScript Types

If using TypeScript, update your type definitions:

```typescript
interface Product {
  id: string;
  company_id: string;
  product_name: string;
  file_name?: string;
  original_filename?: string;
  description?: string;
  product_url?: string;
  enriched_information?: {
    overview?: string;
    key_value_proposition?: string;
    pricing?: string;
    reviews?: string[];
    market_overview?: string;
    competitors?: string;
  };
  created_at?: string;
  deleted: boolean;
}
```

### 3. Testing

Write tests for the new functionality:

```javascript
// Example Jest test
describe('ProductForm', () => {
  it('submits the form with all fields', async () => {
    // Test implementation
  });
  
  it('displays loading state during submission', async () => {
    // Test implementation
  });
  
  it('handles URL validation correctly', async () => {
    // Test implementation
  });
});
```

## Conclusion

The product enrichment feature enhances our product catalog with minimal user effort. By implementing these frontend changes, we provide a seamless experience for users to add detailed product information while leveraging the power of AI to automatically enrich that data.

For any questions or issues with implementation, please contact the backend team. 