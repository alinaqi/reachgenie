# Product Management Frontend Guide

## Product Deletion Implementation

This guide provides instructions for implementing the product deletion functionality in the frontend application.

### API Endpoint

The backend provides a delete endpoint that soft-deletes products (marks them as deleted without actually removing them from the database):

- **Endpoint**: `DELETE /api/companies/{company_id}/products/{product_id}`
- **Authentication**: JWT Bearer token required
- **Path Parameters**:
  - `company_id`: UUID of the company
  - `product_id`: UUID of the product to delete

### Request Format

```typescript
// Example API call using axios
const deleteProduct = async (companyId: string, productId: string) => {
  try {
    const response = await axios.delete(
      `/api/companies/${companyId}/products/${productId}`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      }
    );
    
    return response.data;
  } catch (error) {
    // Handle error
    console.error('Error deleting product:', error);
    throw error;
  }
};
```

### Response Format

```json
{
  "status": "success",
  "message": "Product deleted successfully"
}
```

### Error Responses

| Status Code | Description | Possible Reason |
|-------------|-------------|----------------|
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | User doesn't have access to the company or product belongs to a different company |
| 404 | Not Found | Product or company not found |
| 500 | Server Error | Failed to delete product |

### UI Implementation Guidelines

1. **Confirmation Dialog**:
   - Always show a confirmation dialog before deleting a product
   - Clearly explain that this action cannot be undone
   - Use warning colors to indicate destructive action

2. **Button Placement**:
   - Place delete buttons away from frequently used actions to prevent accidental clicks
   - Consider using an icon (trash/bin) with text for clarity

3. **User Feedback**:
   - Show loading state during deletion
   - Display success message after successful deletion
   - Show clear error message if deletion fails

4. **Product List Updates**:
   - Remove the product from the UI immediately after successful deletion
   - Consider implementing optimistic UI updates (remove from UI before API confirms)
   - Add rollback mechanism if the API call fails

### Example React Component

```tsx
import { useState } from 'react';
import { Button, Modal, message } from 'your-ui-library';

interface DeleteProductModalProps {
  companyId: string;
  product: {
    id: string;
    product_name: string;
  };
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const DeleteProductModal: React.FC<DeleteProductModalProps> = ({
  companyId,
  product,
  isOpen,
  onClose,
  onSuccess
}) => {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deleteProduct(companyId, product.id);
      message.success('Product deleted successfully');
      onSuccess();
    } catch (error) {
      if (error.response?.status === 404) {
        message.error('Product not found');
      } else if (error.response?.status === 403) {
        message.error('You do not have permission to delete this product');
      } else {
        message.error('Failed to delete product. Please try again later.');
      }
    } finally {
      setIsDeleting(false);
      onClose();
    }
  };

  return (
    <Modal 
      title="Delete Product" 
      open={isOpen} 
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          Cancel
        </Button>,
        <Button
          key="delete"
          type="primary"
          danger
          loading={isDeleting}
          onClick={handleDelete}
        >
          Delete
        </Button>
      ]}
    >
      <p>Are you sure you want to delete <strong>{product.product_name}</strong>?</p>
      <p className="text-red-500">This action cannot be undone.</p>
      <p>Note: All related data like call logs and campaign statistics will be preserved.</p>
    </Modal>
  );
};
```

### Integration in Product List

```tsx
import { useState } from 'react';
import { Table, Button, message } from 'your-ui-library';
import { DeleteProductModal } from './DeleteProductModal';

export const ProductList = ({ companyId }) => {
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  
  const fetchProducts = async () => {
    // Fetch products from API
  };
  
  const handleDeleteClick = (product) => {
    setSelectedProduct(product);
    setIsDeleteModalOpen(true);
  };
  
  const handleDeleteSuccess = () => {
    // Remove product from list
    setProducts(products.filter(p => p.id !== selectedProduct.id));
    setSelectedProduct(null);
  };
  
  return (
    <>
      <Table
        dataSource={products}
        columns={[
          {
            title: 'Name',
            dataIndex: 'product_name',
            key: 'product_name',
          },
          {
            title: 'Actions',
            key: 'actions',
            render: (_, product) => (
              <Button 
                type="text" 
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDeleteClick(product)}
              >
                Delete
              </Button>
            ),
          },
        ]}
      />
      
      {selectedProduct && (
        <DeleteProductModal
          companyId={companyId}
          product={selectedProduct}
          isOpen={isDeleteModalOpen}
          onClose={() => setIsDeleteModalOpen(false)}
          onSuccess={handleDeleteSuccess}
        />
      )}
    </>
  );
};
```

### Additional Considerations

1. **Permission Handling**:
   - Only show delete buttons to users with appropriate permissions
   - Check user roles before displaying delete options

2. **Batch Operations**:
   - If implementing batch delete, ensure clear user feedback
   - Consider showing the number of items being deleted

3. **Undo Functionality**:
   - Consider implementing an "undo" option for a short period after deletion
   - This would require additional backend API support

4. **Dependent Resources**:
   - Inform users if the product has campaigns or other dependent resources
   - Explain that these related resources will be preserved

5. **Accessibility**:
   - Ensure all delete buttons and dialogs are keyboard accessible
   - Use appropriate ARIA attributes for screen readers

Remember that product deletion is a soft delete operation - the product is marked as deleted in the database but not physically removed. This preserves all relationships with campaigns, leads, and statistics. 