document.querySelector('input[name="document"]').addEventListener('change', function(event) {
    const preview = document.getElementById('preview');
    preview.innerHTML = '';

    for (let file of event.target.files) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = document.createElement('img');
            img.src = e.target.result;
            img.classList.add('m-2');
            img.style.width = '70px';
            img.style.height = '100px';
            img.style.objectFit = 'cover';
            preview.appendChild(img);
        }
        reader.readAsDataURL(file);
    }
});

$(document).on('click', '.edit-expense-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#expenseForm').attr('action', '/admin-panel/expense/edit/' + id + '/');

    // Populate the form with the expense data
    $('#id_category').val($(this).data('category')).trigger('change');
    $('#id_amount').val($(this).data('amount'));

    // Ensure date is in YYYY-MM-DD format before setting it
    var expenseDate = $(this).data('date');
    // If the date is in a format other than YYYY-MM-DD, convert it here
    // You can use moment.js or another library for conversion if necessary
    $('#id_date').val(expenseDate);  // Assuming it's already in correct format

    $('#id_doc_no').val($(this).data('doc_no'));
    $('#id_description').val($(this).data('description'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    $('#exampleModalLongTitle').text('ویرایش هزینه');
    $('#btn-submit-expense').text('ویرایش هزینه');
});
