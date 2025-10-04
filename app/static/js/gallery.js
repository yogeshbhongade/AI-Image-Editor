// ============================================================
// IMAGE GALLERY JAVASCRIPT
// Handles my images page, deletion, and gallery functions
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeGallery();
});

function initializeGallery() {
    // Initialize delete functionality
    setupDeleteButtons();
    
    // Initialize bulk selection
    setupBulkSelection();
    
    // Initialize image preview
    setupImagePreview();
    
    // Initialize pagination
    setupPagination();
    
    // Initialize search and filter
    setupSearchAndFilter();
}

function setupDeleteButtons() {
    document.querySelectorAll('[data-delete-id]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const imageId = btn.getAttribute('data-delete-id');
            const imageName = btn.getAttribute('data-image-name') || 'this image';
            
            if (confirm(`Are you sure you want to delete "${imageName}"? This action cannot be undone.`)) {
                deleteImage(imageId, btn);
            }
        });
    });
}

function deleteImage(imageId, button) {
    ImageCraftApp.setLoading(button, true);
    
    ImageCraftApp.makeRequest('/delete-image', {
        method: 'POST',
        body: JSON.stringify({ image_id: imageId })
    })
    .then(response => {
        if (response.success) {
            // Remove the image card from DOM
            const imageCard = button.closest('.image-card');
            if (imageCard) {
                imageCard.style.opacity = '0';
                imageCard.style.transform = 'scale(0.8)';
                
                setTimeout(() => {
                    imageCard.remove();
                    updateImageCount();
                }, 300);
            }
            
            ImageCraftApp.showFlashMessage('Image deleted successfully', 'success');
        } else {
            throw new Error(response.error || 'Failed to delete image');
        }
    })
    .catch(error => {
        console.error('Delete failed:', error);
        ImageCraftApp.showFlashMessage('Failed to delete image: ' + error.message, 'error');
    })
    .finally(() => {
        ImageCraftApp.setLoading(button, false);
    });
}

function setupBulkSelection() {
    const selectAllCheckbox = document.getElementById('select-all');
    const imageCheckboxes = document.querySelectorAll('.image-checkbox');
    const bulkDeleteBtn = document.getElementById('bulk-delete');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', () => {
            imageCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateBulkActions();
        });
    }
    
    imageCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkActions);
    });
    
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', handleBulkDelete);
    }
}

function updateBulkActions() {
    const selectedCheckboxes = document.querySelectorAll('.image-checkbox:checked');
    const bulkActions = document.getElementById('bulk-actions');
    const bulkDeleteBtn = document.getElementById('bulk-delete');
    const selectedCount = document.getElementById('selected-count');
    
    if (selectedCheckboxes.length > 0) {
        bulkActions?.classList.add('active');
        if (selectedCount) selectedCount.textContent = selectedCheckboxes.length;
    } else {
        bulkActions?.classList.remove('active');
    }
}

function handleBulkDelete() {
    const selectedCheckboxes = document.querySelectorAll('.image-checkbox:checked');
    const selectedIds = Array.from(selectedCheckboxes).map(cb => cb.value);
    
    if (selectedIds.length === 0) {
        ImageCraftApp.showFlashMessage('No images selected', 'warning');
        return;
    }
    
    if (!confirm(`Are you sure you want to delete ${selectedIds.length} selected images? This action cannot be undone.`)) {
        return;
    }
    
    const bulkDeleteBtn = document.getElementById('bulk-delete');
    ImageCraftApp.setLoading(bulkDeleteBtn, true);
    
    // Delete images one by one
    Promise.all(selectedIds.map(imageId => {
        return ImageCraftApp.makeRequest('/delete-image', {
            method: 'POST',
            body: JSON.stringify({ image_id: imageId })
        });
    }))
    .then(responses => {
        const successCount = responses.filter(r => r.success).length;
        const failCount = responses.length - successCount;
        
        // Remove successful deletions from DOM
        selectedCheckboxes.forEach(checkbox => {
            const imageCard = checkbox.closest('.image-card');
            if (imageCard) {
                imageCard.style.opacity = '0';
                imageCard.style.transform = 'scale(0.8)';
                
                setTimeout(() => {
                    imageCard.remove();
                }, 300);
            }
        });
        
        updateImageCount();
        
        if (failCount === 0) {
            ImageCraftApp.showFlashMessage(`Successfully deleted ${successCount} images`, 'success');
        } else {
            ImageCraftApp.showFlashMessage(`Deleted ${successCount} images, ${failCount} failed`, 'warning');
        }
    })
    .catch(error => {
        console.error('Bulk delete failed:', error);
        ImageCraftApp.showFlashMessage('Bulk delete failed: ' + error.message, 'error');
    })
    .finally(() => {
        ImageCraftApp.setLoading(bulkDeleteBtn, false);
        updateBulkActions();
    });
}

function setupImagePreview() {
    document.querySelectorAll('.image-preview[data-bg-url]').forEach(el => {
        const url = el.getAttribute('data-bg-url');
        if (url) {
            el.style.backgroundImage = `url('${url}')`;
        } else {
            el.style.backgroundImage = '';
        }
    });

    document.querySelectorAll('.image-preview').forEach(preview => {
        preview.addEventListener('click', () => {
            // Use data-bg-url instead of regex parsing
            const imageSrc = preview.getAttribute('data-bg-url');
            if (imageSrc) {
                showImageModal(imageSrc);
            }
        });
    });
}

function showImageModal(imageSrc) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('image-modal');
    if (!modal) {
        modal = createImageModal();
    }
    
    const modalImg = modal.querySelector('.modal-image');
    if (modalImg) {
        modalImg.src = imageSrc;
        modalImg.onload = () => {
            ImageCraftApp.openModal('image-modal');
            document.getElementById('image-modal')?.classList.add('open');
        };
    }
}

function createImageModal() {
    const modal = document.createElement('div');
    modal.id = 'image-modal';
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content image-modal-content">
            <span class="modal-close">&times;</span>
            <img class="modal-image" alt="Preview">
            <div class="modal-controls">
                <button onclick="downloadCurrentImage()" class="btn btn-primary">
                    <i class="fa-solid fa-download"></i> Download
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add close functionality
    modal.querySelector('.modal-close').addEventListener('click', () => {
        ImageCraftApp.closeModal('image-modal');
        document.getElementById('image-modal')?.classList.remove('open');
    });
    
    return modal;
}

function downloadCurrentImage() {
    const modal = document.getElementById('image-modal');
    const modalImg = modal?.querySelector('.modal-image');
    
    if (modalImg && modalImg.src) {
        const link = document.createElement('a');
        link.href = modalImg.src;
        link.download = 'image.jpg';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        ImageCraftApp.showFlashMessage('Download started!', 'success');
    }
}

function setupPagination() {
    document.querySelectorAll('.pagination a').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const href = link.getAttribute('href');
            
            // Show loading state
            ImageCraftApp.showFlashMessage('Loading images...', 'info');
            
            // Navigate to the page
            window.location.href = href;
        });
    });
}

function setupSearchAndFilter() {
    const searchInput = document.getElementById('image-search');
    const filterSelect = document.getElementById('image-filter');
    
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                filterImages(searchInput.value, filterSelect?.value);
            }, 300);
        });
    }
    
    if (filterSelect) {
        filterSelect.addEventListener('change', () => {
            filterImages(searchInput?.value, filterSelect.value);
        });
    }
}

function filterImages(searchTerm = '', filterType = 'all') {
    const imageCards = document.querySelectorAll('.image-card');
    let visibleCount = 0;
    
    imageCards.forEach(card => {
        const imageName = card.querySelector('.image-title')?.textContent?.toLowerCase() || '';
        const imageOperation = card.getAttribute('data-operation')?.toLowerCase() || '';
        const imageDate = card.getAttribute('data-date') || '';
        
        let shouldShow = true;
        
        // Apply search filter
        if (searchTerm) {
            const searchLower = searchTerm.toLowerCase();
            shouldShow = imageName.includes(searchLower) || 
                        imageOperation.includes(searchLower) || 
                        imageDate.includes(searchLower);
        }
        
        // Apply type filter
        if (filterType !== 'all' && shouldShow) {
            shouldShow = imageOperation.includes(filterType);
        }
        
        // Show/hide card
        if (shouldShow) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    // Update results count
    const resultsCount = document.getElementById('results-count');
    if (resultsCount) {
        resultsCount.textContent = `Showing ${visibleCount} images`;
    }
    
    // Show no results message
    const noResults = document.getElementById('no-results');
    if (noResults) {
        noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }
}

function updateImageCount() {
    const imageCards = document.querySelectorAll('.image-card').length;
    const countElements = document.querySelectorAll('.image-count');
    
    countElements.forEach(element => {
        element.textContent = imageCards;
    });
    
    // If no images left, show empty state
    if (imageCards === 0) {
        showEmptyState();
    }
}

function showEmptyState() {
    const gallery = document.querySelector('.images-grid');
    if (gallery) {
        gallery.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-content">
                    <i class="fa-solid fa-images empty-state-icon"></i>
                    <h3>No images found</h3>
                    <p>You haven't edited any images yet. Start creating!</p>
                    <a href="/editing" class="btn btn-primary">
                        <i class="fa-solid fa-plus"></i> Upload & Edit First Image
                    </a>
                </div>
            </div>
        `;
    }
}

// Export functions
window.ImageGallery = {
    deleteImage,
    showImageModal,
    downloadCurrentImage,
    filterImages,
    handleBulkDelete
};
