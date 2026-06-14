
    $(document).ready(function() {
        // Function to get the CSRF token from the cookie
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        const csrfToken = getCookie('csrftoken');

        // Handle delete button click
        $('#deleteModal').on('show.bs.modal', function (event) {
            var button = $(event.relatedTarget); // Button that triggered the modal
            var productId = button.data('id'); // Extract info from data-* attributes

            var modal = $(this);
            modal.find('#confirmDelete').off('click').on('click', function() {
                $.ajax({
                    url: '/delete-product/' + productId + '/', // URL of your delete view
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    success: function(response) {
                        if (response.success) {
                            // Display success message
                            $('.container').prepend('<div class="alert alert-success" role="alert">' + response.message + '</div>');
                            // Reload the page after successful deletion
                            setTimeout(function() {
                                location.reload();
                            }, 2000);
                        } else {
                            // Display error message
                            $('.container').prepend('<div class="alert alert-danger" role="alert">' + response.message + '</div>');
                        }
                    },
                    error: function(xhr, errmsg, err) {
                        $('.container').prepend('<div class="alert alert-danger" role="alert">Error: ' + errmsg + '</div>');
                    }
                });
            });
        });
    });


        $(document).ready(function() {

            // Handle edit button click
            $('#editModal').on('show.bs.modal', function (event) {
                var button = $(event.relatedTarget); // Button that triggered the modal
                var productId = button.data('id'); // Extract info from data-* attributes

                // Populate the modal fields with data
                var modal = $(this);
                modal.find('#product_id').val(productId);
                modal.find('#material_name').val(button.data('name'));
                modal.find('#supplier_name').val(button.data('supplier'));
                modal.find('#supplier_contact').val(button.data('contact'));
                modal.find('#total_quantity').val(button.data('quantity'));
                modal.find('#unit_price').val(button.data('price'));
                modal.find('#total_price').val(button.data('total'));
                modal.find('#purchase_date').val(button.data('date'));
            });

            // Handle form submission in edit modal
            $('#editForm').on('submit', function(event) {
                event.preventDefault(); // Prevent the form from submitting the traditional way

                $.ajax({
                    url: '/update-product/', // URL of your update view
                    type: 'POST',
                    data: $(this).serialize(), // Serialize form data
                    success: function(response) {
                        if (response.success) {
                            // Display success message
                            $('.container').prepend('<div class="alert alert-success" role="alert">' + response.message + '</div>');
                            // Reload the page after successful update
                            setTimeout(function() {
                                location.reload();
                            }, 2000);
                        } else {
                            // Display error message
                            $('.container').prepend('<div class="alert alert-danger" role="alert">' + response.message + '</div>');
                        }
                    },
                    error: function(xhr, errmsg, err) {
                        $('.container').prepend('<div class="alert alert-danger" role="alert">Error: ' + errmsg + '</div>');
                    }
                });
            });
        });
