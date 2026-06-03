document.addEventListener('DOMContentLoaded', function() {
    // 1. AJAX for Admin Toggle Status (Freeze/Unfreeze)
    const statusButtons = document.querySelectorAll('.btn-toggle-status');
    statusButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const userId = this.dataset.userId;
            const url = `/admin/api/user/${userId}/toggle-status`;
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            fetch(url, { 
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Update Badge
                        const badge = document.querySelector(`#status-badge-${userId}`);
                        badge.textContent = data.new_status;
                        badge.className = `status-badge ${data.new_status.toLowerCase()}`;
                        
                        // Update Button
                        this.textContent = data.new_status === 'Active' ? 'Freeze' : 'Unfreeze';
                        this.className = `btn btn-sm ${data.new_status === 'Active' ? 'btn-danger' : 'btn-success'} btn-toggle-status`;
                        
                        showToast(data.message, 'success');
                    } else {
                        showToast(data.message, 'danger');
                    }
                });
        });
    });

    // 2. AJAX for Transaction Approval/Rejection
    const txActions = document.querySelectorAll('.tx-action-btn');
    let activeTxId = null;

    txActions.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const txId = this.dataset.txId;
            const action = this.dataset.action; // approve or reject
            
            if (action === 'reject') {
                activeTxId = txId;
                document.getElementById('rejectionModal').style.display = 'flex';
                return;
            }
            
            processTransaction(txId, 'approve');
        });
    });

    window.closeRejectionModal = function() {
        document.getElementById('rejectionModal').style.display = 'none';
        document.getElementById('modalReason').value = '';
    };

    const confirmRejectBtn = document.getElementById('confirmRejectionBtn');
    if (confirmRejectBtn) {
        confirmRejectBtn.addEventListener('click', function() {
            const reason = document.getElementById('modalReason').value || "Insufficient documentation";
            processTransaction(activeTxId, 'reject', reason);
            closeRejectionModal();
        });
    }

    function processTransaction(txId, action, reason = null) {
        const url = `/admin/api/transaction/${txId}/${action}`;
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        
        let payload = {};
        if (reason) payload.reason = reason;
        
        fetch(url, { 
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const row = document.querySelector(`#tx-row-${txId}`);
                    if (row) {
                        row.classList.add('fade-out');
                        setTimeout(() => row.remove(), 500);
                    }
                    showToast(data.message, 'success');
                } else {
                    showToast(data.message, 'danger');
                }
            });
    }

    // 3. Live Recipient Verification for Transfers
    const recipientInput = document.querySelector('#recipient-email');
    const recipientFeedback = document.querySelector('#recipient-feedback');
    if (recipientInput) {
        recipientInput.addEventListener('blur', function() {
            const email = this.value;
            if (email.length > 3) {
                fetch(`/banking/api/verify-recipient?email=${encodeURIComponent(email)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.exists) {
                            recipientFeedback.textContent = `✓ Recipient found: ${data.username}`;
                            recipientFeedback.style.color = '#00ff88';
                        } else {
                            recipientFeedback.textContent = `✗ Recipient not found.`;
                            recipientFeedback.style.color = '#ff4757';
                        }
                    });
            }
        });
    }

    // Toast Utility
    function showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} toast-notification`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 500);
            }, 3000);
        }, 100);
    }
});
