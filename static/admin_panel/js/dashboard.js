$('#myForm').on('submit', function(e){
  $('#myModal').modal('show');
  e.preventDefault();
});
// ====================
function updateClock() {
    var sundte = new Date();
    var hours = sundte.getHours();
    var minutes = sundte.getMinutes();
    var seconds = sundte.getSeconds();

    document.getElementById("time").innerHTML = "ساعت " + hours + ":" + minutes + ":" + seconds;
}

// Call updateClock every second (1000 milliseconds)
setInterval(updateClock, 1000);


var sundte = new Date();
var yeardte = sundte.getFullYear();
var monthdte = sundte.getMonth();
var dtedte = sundte.getDate();
var daydte = sundte.getDay();
var sunyear;

switch (daydte) {
    case 0:
        var today = "يکشنبه";
        break;
    case 1:
        var today = "دوشنبه";
        break;
    case 2:
        var today = "سه شنبه";
        break;
    case 3:
        var today = "چهارشنبه";
        break;
    case 4:
        var today = "پنجشنبه";
        break;
    case 5:
        var today = "جمعه";
        break;
    case 6:
        var today = "شنبه";
        break;
}
switch (monthdte) {
    case 0:
        sunyear = yeardte - 622;
        if (dtedte <= 20) {
            var sunmonth = "دي";
            var daysun = dtedte + 10;
        } else {
            var sunmonth = "بهمن";
            var daysun = dtedte - 20;
        }
        break;
    case 1:
        sunyear = yeardte - 622;
        if (dtedte <= 19) {
            var sunmonth = "بهمن";
            var daysun = dtedte + 11;
        } else {
            var sunmonth = "اسفند";
            var daysun = dtedte - 19;
        }
        break;
    case 2: {
        if ((yeardte - 621) % 4 == 0) var i = 10;
        else var i = 9;
        if (dtedte <= 20) {
            sunyear = yeardte - 622;
            var sunmonth = "اسفند";
            var daysun = dtedte + i;
        } else {
            sunyear = yeardte - 621;
            var sunmonth = "فروردين";
            var daysun = dtedte - 20;
        }
    }
        break;
    case 3:
        sunyear = yeardte - 621;
        if (dtedte <= 20) {
            var sunmonth = "فروردين";
            var daysun = dtedte + 10;
        } else {
            var sunmonth = "ارديبهشت";
            var daysun = dtedte - 20;
        }
        break;
    case 4:
        sunyear = yeardte - 621;
        if (dtedte <= 21) {
            var sunmonth = "ارديبهشت";
            var daysun = dtedte + 10;
        } else {
            var sunmonth = "خرداد";
            var daysun = dtedte - 21;
        }

        break;
    case 5:
        sunyear = yeardte - 621;
        if (dtedte <= 21) {
            var sunmonth = "خرداد";
            var daysun = dtedte + 10;
        } else {
            var sunmonth = "تير";
            var daysun = dtedte - 21;
        }
        break;
    case 6:
        sunyear = yeardte - 621;
        if (dtedte <= 22) {
            var sunmonth = "تير";
            var daysun = dtedte + 9;
        } else {
            var sunmonth = "مرداد";
            var daysun = dtedte - 22;
        }
        break;
    case 7:
        sunyear = yeardte - 621;
        if (dtedte <= 22) {
            var sunmonth = "مرداد";
            var daysun = dtedte + 9;
        } else {
            var sunmonth = "شهريور";
            var daysun = dtedte - 22;
        }
        break;
    case 8:
        sunyear = yeardte - 621;
        if (dtedte <= 22) {
            var sunmonth = "شهريور";
            var daysun = dtedte + 9;
        } else {
            var sunmonth = "مهر";
            var daysun = dtedte - 22;
        }
        break;
    case 9:
        sunyear = yeardte - 621;
        if (dtedte <= 22) {
            var sunmonth = "مهر";
            var daysun = dtedte + 8;
        } else {
            var sunmonth = "آبان";
            var daysun = dtedte - 22;
        }
        break;
    case 10:
        sunyear = yeardte - 621;
        if (dtedte <= 21) {
            var sunmonth = "آبان";
            var daysun = dtedte + 9;
        } else {
            var sunmonth = "آذر";
            var daysun = dtedte - 21;
        }

        break;
    case 11:
        sunyear = yeardte - 621;
        if (dtedte <= 19) {
            var sunmonth = "آذر";
            var daysun = dtedte + 9;
        } else {
            var sunmonth = "دي";
            var daysun = dtedte - 21;
        }
        break;
}
document.getElementById("demo").innerHTML =
    "امروز: " +
    today +
    "&nbsp;" +
    [daysun + 1] +
    "&nbsp;" +
    sunmonth +
    "&nbsp;" +
    sunyear +
    " ";
// ======================================================

$(document).on('click', '.edit-expense-btn', function (e) {
    e.preventDefault();

    var images = $(this).data('images');
    var expenseId = $(this).data('id');  // ← گرفتن expense_id صحیح

    if (typeof images === 'string') {
        try {
            images = JSON.parse(images);
        } catch (error) {
            console.error('Error parsing images JSON:', error);
            images = [];
        }
    }

    $('#preview').empty();

    if (images.length > 0) {
        images.forEach(function(imgUrl, index) {
            var imageWrapper = `
                <div class="image-item m-2 position-relative" style="display:inline-block;">
                    <img src="${imgUrl}"
                         style="width: 100px; height: 100px; object-fit: cover; border: 1px solid #ccc;">
                    <button type="button" class="btn btn-sm btn-danger delete-image321-btn"
                            data-url="${imgUrl}"
                            data-expense-id="${expenseId}"
                            style="position: absolute; top: -5px; right: -5px; border-radius: 50%;">
                        ×
                    </button>
                </div>
            `;
            $('#preview').append(imageWrapper);
        });
    } else {
        $('#preview').html('<p>تصویری وجود ندارد.</p>');
    }
});



$(document).on('click', '.delete-image321-btn', function () {
    var imageUrl = $(this).data('url');  // Image URL
    var expenseId = $(this).data('expense-id');  // Expense ID
    console.log(expenseId)

    if (!imageUrl || !expenseId) {
        Swal.fire('خطا', 'URL یا ID هزینه مشخص نیست', 'error');
        return;
    }

    Swal.fire({
        title: 'آیا مطمئنی میخوای این تصویر رو حذف کنی؟',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'بله، حذف کن!',
        cancelButtonText: 'لغو'
    }).then((result) => {
        if (result.isConfirmed) {
            // Send the request to delete the image
            $.ajax({
                type: 'POST',
                url: '/admin-panel/expense/delete-document/',  // Your delete URL
                data: {
                    csrfmiddlewaretoken: '{{ csrf_token }}',  // Ensure CSRF token is included
                    url: imageUrl,  // The URL of the image to delete
                    expense_id: expenseId  // The ID of the related expense
                },
                success: function(response) {
                    if (response.status === 'success') {
                        Swal.fire('حذف شد!', 'تصویر با موفقیت حذف شد.', 'success');
                        // Optionally, remove the image from the preview
                        $(`[data-url="${imageUrl}"]`).closest('.image-item').remove();
                    } else {
                        Swal.fire('خطا', response.message, 'error');
                    }
                },
                error: function() {
                    Swal.fire('خطا', 'خطا در حذف تصویر', 'error');
                }
            });
        }
    });
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
 document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('personForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

// ==========================================
$(document).on('click', '.edit-income-btn', function (e) {
    e.preventDefault();

    var images = $(this).data('images');
    var incomeId = $(this).data('id');  // ← گرفتن expense_id صحیح

    if (typeof images === 'string') {
        try {
            images = JSON.parse(images);
        } catch (error) {
            console.error('Error parsing images JSON:', error);
            images = [];
        }
    }

    $('#preview').empty();

    if (images.length > 0) {
        images.forEach(function(imgUrl, index) {
            var imageWrapper = `
                <div class="image-item m-2 position-relative" style="display:inline-block;">
                    <img src="${imgUrl}"
                         style="width: 100px; height: 100px; object-fit: cover; border: 1px solid #ccc;">
                    <button type="button" class="btn btn-sm btn-danger delete-image21-btn"
                            data-url="${imgUrl}"
                            data-income-id="${incomeId}"
                            style="position: absolute; top: -5px; right: -5px; border-radius: 50%;">
                        ×
                    </button>
                </div>
            `;
            $('#preview').append(imageWrapper);
        });
    } else {
        $('#preview').html('<p>تصویری وجود ندارد.</p>');
    }
});

$(document).on('click', '.delete-image21-btn', function () {
    var imageUrl = $(this).data('url');  // Image URL
    var incomeId = $(this).data('income-id');  // Expense ID


    if (!imageUrl || !incomeId) {
        Swal.fire('خطا', 'URL یا ID هزینه مشخص نیست', 'error');
        return;
    }

    Swal.fire({
        title: 'آیا مطمئنی میخوای این تصویر رو حذف کنی؟',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'بله، حذف کن!',
        cancelButtonText: 'لغو'
    }).then((result) => {
        if (result.isConfirmed) {
            // Send the request to delete the image
            $.ajax({
                type: 'POST',
                url: '/admin-panel/income/delete-document/',  // Your delete URL
                data: {
                    csrfmiddlewaretoken: '{{ csrf_token }}',  // Ensure CSRF token is included
                    url: imageUrl,  // The URL of the image to delete
                    income_id: incomeId  // The ID of the related expense
                },
                success: function(response) {
                    if (response.status === 'success') {
                        Swal.fire('حذف شد!', 'تصویر با موفقیت حذف شد.', 'success');
                        // Optionally, remove the image from the preview
                        $(`[data-url="${imageUrl}"]`).closest('.image-item').remove();
                    } else {
                        Swal.fire('خطا2', response.message, 'error');
                    }
                },
                error: function() {
                    Swal.fire('خطا', 'خطا در حذف تصویر', 'error');
                }
            });
        }
    });
});

$(document).on('click', '.edit-bank-btn', function () {
    console.log('ویرایش کلیک شد2');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    $('#bankForm').attr('action', '/admin-panel/bank/edit/' + id + '/');

    // Populate the form with the expense data
    $('#id_bank_name').val($(this).data('bank_name'));
    $('#id_account_holder_name').val($(this).data('account_holder_name'));
    $('#id_account_no').val($(this).data('account_no'));
    $('#id_sheba_number').val($(this).data('sheba_number'));
    $('#id_cart_number').val($(this).data('cart_number'));
    $('#id_initial_fund').val($(this).data('initial_fund').toString().replace(/,/g, ''));

    // Update the modal title and submit button text for editing
    $('#exampleModalLongTitle3').text('ویرایش حساب بانکی');
    $('#btn-submit-bank').text('ویرایش حساب بانکی');
});
 document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('personForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

// ===================================================
$(document).on('click', '.edit-receive-btn', function (e) {
    e.preventDefault();

    var images = $(this).data('images');
    var receiveId = $(this).data('id');  //

    if (typeof images === 'string') {
        try {
            images = JSON.parse(images);
        } catch (error) {
            console.error('Error parsing images JSON:', error);
            images = [];
        }
    }

    $('#preview').empty();

    if (images.length > 0) {
        images.forEach(function(imgUrl, index) {
            var imageWrapper = `
                <div class="image-item m-2 position-relative" style="display:inline-block;">
                    <img src="${imgUrl}"
                         style="width: 100px; height: 100px; object-fit: cover; border: 1px solid #ccc;">
                    <button type="button" class="btn btn-sm btn-danger delete-image1-btn"
                            data-url="${imgUrl}"
                            data-receive-id="${receiveId}"
                            style="position: absolute; top: -5px; right: -5px; border-radius: 50%;">
                        ×
                    </button>
                </div>
            `;
            $('#preview').append(imageWrapper);
        });
    } else {
        $('#preview').html('<p>تصویری وجود ندارد.</p>');
    }
});

$(document).on('click', '.delete-image1-btn', function () {
    var imageUrl = $(this).data('url');  // Image URL
    var receiveId = $(this).data('receive-id');


    if (!imageUrl || !receiveId) {
        Swal.fire('خطا', 'URL یا ID هزینه مشخص نیست', 'error');
        return;
    }

    Swal.fire({
        title: 'آیا مطمئنی میخوای این تصویر رو حذف کنی؟',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'بله، حذف کن!',
        cancelButtonText: 'لغو'
    }).then((result) => {
        if (result.isConfirmed) {
            // Send the request to delete the image
            $.ajax({
                type: 'POST',
                url: '/admin-panel/receive/delete-document/',  // Your delete URL
                data: {
                    csrfmiddlewaretoken: '{{ csrf_token }}',  // Ensure CSRF token is included
                    url: imageUrl,  // The URL of the image to delete
                    receive_id: receiveId  // The ID of the related expense
                },
                success: function(response) {
                    if (response.status === 'success') {
                        Swal.fire('حذف شد!', 'تصویر با موفقیت حذف شد.', 'success');
                        // Optionally, remove the image from the preview
                        $(`[data-url="${imageUrl}"]`).closest('.image-item').remove();
                    } else {
                        Swal.fire('خطا2', response.message, 'error');
                    }
                },
                error: function() {
                    Swal.fire('خطا', 'خطا در حذف تصویر', 'error');
                }
            });
        }
    });
});

$(document).on('click', '.edit-receive-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#receiveForm').attr('action', '/admin-panel/receive/edit/' + id + '/');

    // Populate the form with the expense data
    $('#id_bank').val($(this).data('bank')).trigger('change');
    $('#id_amount').val($(this).data('amount'));
    $('#id_payer_name').val($(this).data('payer_name'));

    // Ensure date is in YYYY-MM-DD format before setting it
    var receiveDate = $(this).data('doc_date');
    // If the date is in a format other than YYYY-MM-DD, convert it here
    // You can use moment.js or another library for conversion if necessary
    $('#id_doc_date').val(receiveDate);  // Assuming it's already in correct format

    $('#id_doc_number').val($(this).data('doc_number'));
    $('#id_description').val($(this).data('description'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    $('#exampleModalLongTitle').text('ویرایش سند دریافتنی');
    $('#btn-submit-receive').text('ویرایش سند دریافتنی');
});

 document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('personForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });
// ================================================= pay ====
$(document).on('click', '.edit-pay-btn', function (e) {
    e.preventDefault();

    var images = $(this).data('images');
    var paymentId = $(this).data('id');  //

    if (typeof images === 'string') {
        try {
            images = JSON.parse(images);
        } catch (error) {
            console.error('Error parsing images JSON:', error);
            images = [];
        }
    }

    $('#preview').empty();

    if (images.length > 0) {
        images.forEach(function(imgUrl, index) {
            var imageWrapper = `
                <div class="image-item m-2 position-relative" style="display:inline-block;">
                    <img src="${imgUrl}"
                         style="width: 100px; height: 100px; object-fit: cover; border: 1px solid #ccc;">
                    <button type="button" class="btn btn-sm btn-danger delete-image_payment-btn"
                            data-url="${imgUrl}"
                            data-payment-id="${paymentId}"
                            style="position: absolute; top: -5px; right: -5px; border-radius: 50%;">
                        ×
                    </button>
                </div>
            `;
            $('#preview').append(imageWrapper);
        });
    } else {
        $('#preview').html('<p>تصویری وجود ندارد.</p>');
    }
});

$(document).on('click', '.delete-image_payment-btn', function () {
    const imageUrl = $(this).data('url');
    const paymentId = $(this).data('payment-id');
    const button = $(this);


    if (!imageUrl || !paymentId) {
        Swal.fire('خطا', 'URL یا ID هزینه مشخص نیست', 'error');
        return;
    }

    Swal.fire({
        title: 'آیا مطمئنی میخوای این تصویر رو حذف کنی؟',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'بله، حذف کن!',
        cancelButtonText: 'لغو'
    }).then((result) => {
        if (result.isConfirmed) {
            // Send the request to delete the image
            $.ajax({
                type: 'POST',
                url: '/admin-panel/pay/delete-document/',  // Your delete URL
                data: {
                    csrfmiddlewaretoken: '{{ csrf_token }}',  // Ensure CSRF token is included
                    url: imageUrl,  // The URL of the image to delete
                    payment_id: paymentId  // The ID of the related expense
                },
                success: function(response) {
                    if (response.status === 'success') {
                        Swal.fire('حذف شد!', 'تصویر با موفقیت حذف شد.', 'success');
                        button.closest('.image-item').remove();
                    } else {
                        Swal.fire('خطا', response.message, 'error');
                    }
                },
                error: function() {
                    Swal.fire('خطا', 'خطا در حذف تصویر', 'error');
                }
            });
        }
    });
});
$(document).on('click', '.edit-pay-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#receiveForm').attr('action', '/admin-panel/pay/edit/' + id + '/');

    // Populate the form with the expense data
    $('#id_bank').val($(this).data('bank')).trigger('change');
    $('#id_amount').val($(this).data('amount'));
    $('#id_receiver_name').val($(this).data('receiver_name'));

    // Ensure date is in YYYY-MM-DD format before setting it
    var receiveDate = $(this).data('document_date');
    // If the date is in a format other than YYYY-MM-DD, convert it here
    // You can use moment.js or another library for conversion if necessary
    $('#id_document_date').val(receiveDate);  // Assuming it's already in correct format

    $('#id_document_number').val($(this).data('document_number'));
    $('#id_description').val($(this).data('description'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    $('#exampleModalLongTitle').text('ویرایش سند پرداختنی');
    $('#btn-submit-receive').text('ویرایش سند پرداختنی');
});
 document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('personForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

// =============================== Property ==================
$(document).on('click', '.edit-property-btn', function (e) {
    e.preventDefault();

    var images = $(this).data('images');
    var propertyId = $(this).data('id');  //

    if (typeof images === 'string') {
        try {
            images = JSON.parse(images);
        } catch (error) {
            console.error('Error parsing images JSON:', error);
            images = [];
        }
    }

    $('#preview').empty();

    if (images.length > 0) {
        images.forEach(function(imgUrl, index) {
            var imageWrapper = `
                <div class="image-item m-2 position-relative" style="display:inline-block;">
                    <img src="${imgUrl}"
                         style="width: 100px; height: 100px; object-fit: cover; border: 1px solid #ccc;">
                    <button type="button" class="btn btn-sm btn-danger delete-image2-btn"
                            data-url="${imgUrl}"
                            data-property-id="${propertyId}"
                            style="position: absolute; top: -5px; right: -5px; border-radius: 50%;">
                        ×
                    </button>
                </div>
            `;
            $('#preview').append(imageWrapper);
        });
    } else {
        $('#preview').html('<p>تصویری وجود ندارد.</p>');
    }
});

$(document).on('click', '.delete-image2-btn', function () {
    const imageUrl = $(this).data('url');
    const propertyId = $(this).data('property-id');
    const button = $(this);  // Save reference for removal later

    if (!imageUrl || !propertyId) {
        Swal.fire('خطا', 'آدرس یا شناسه نگهداری مشخص نیست2.', 'error');
        return;
    }

    Swal.fire({
        title: 'آیا مطمئنی می‌خواهی این تصویر را حذف کنی؟',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'بله، حذف کن!',
        cancelButtonText: 'لغو'
    }).then((result) => {
        if (result.isConfirmed) {
            $.ajax({
                type: 'POST',
                url: '/admin-panel/property/delete-document/',
                data: {
                    url: imageUrl,
                    property_id: propertyId
                },
                success: function(response) {
                    if (response.status === 'success') {
                        Swal.fire('حذف شد!', 'تصویر با موفقیت حذف شد.', 'success');
                        button.closest('.image-item').remove();
                    } else {
                        Swal.fire('خطا', response.message, 'error');
                    }
                },
                error: function() {
                    Swal.fire('خطا', 'خطا در حذف تصویر', 'error');
                }
            });
        }
    });
});
$(document).on('click', '.edit-property-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#propertyForm').attr('action', '/admin-panel/property/edit/' + id + '/');

    $('#id_property_name').val($(this).data('property_name'));
    $('#id_property_unit').val($(this).data('property_unit'));

    // Ensure date is in YYYY-MM-DD format before setting it
    var propertyDate = $(this).data('property_purchase_date');
    // If the date is in a format other than YYYY-MM-DD, convert it here
    // You can use moment.js or another library for conversion if necessary
    $('#id_property_purchase_date').val(propertyDate);  // Assuming it's already in correct format

    $('#id_property_location').val($(this).data('property_location'));
    $('#id_property_price').val($(this).data('property_price'));
    $('#id_property_code').val($(this).data('property_code'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    $('#exampleModalLongTitle').text('ویرایش اموال');
    $('#btn-submit-receive').text('ویرایش اموال');
});
 document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('personForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

// =============================== Maintenance ==================
$(document).on('click', '.edit-maintenance-btn', function (e) {
    e.preventDefault();

    var images = $(this).data('images');
    var maintenanceId = $(this).data('id');  //

    if (typeof images === 'string') {
        try {
            images = JSON.parse(images);
        } catch (error) {
            console.error('Error parsing images JSON:', error);
            images = [];
        }
    }

    $('#preview').empty();

    if (images.length > 0) {
        images.forEach(function(imgUrl, index) {
            var imageWrapper = `
                <div class="image-item m-2 position-relative" style="display:inline-block;">
                    <img src="${imgUrl}"
                         style="width: 100px; height: 100px; object-fit: cover; border: 1px solid #ccc;">
                    <button type="button" class="btn btn-sm btn-danger delete-image-btn"
                            data-url="${imgUrl}"
                            data-maintenance-id="${maintenanceId}"
                            style="position: absolute; top: -5px; right: -5px; border-radius: 50%;">
                        ×
                    </button>
                </div>
            `;
            $('#preview').append(imageWrapper);
        });
    } else {
        $('#preview').html('<p>تصویری وجود ندارد.</p>');
    }
});

$(document).on('click', '.delete-image-btn', function () {
    const imageUrl = $(this).data('url');
    const maintenanceId = $(this).data('maintenance-id');
    const button = $(this);  // Save reference for removal later

    if (!imageUrl || !maintenanceId) {
        Swal.fire('خطا', 'آدرس یا شناسه نگهداری مشخص نیست4.', 'error');
        return;
    }

    Swal.fire({
        title: 'آیا مطمئنی می‌خواهی این تصویر را حذف کنی؟',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'بله، حذف کن!',
        cancelButtonText: 'لغو'
    }).then((result) => {
        if (result.isConfirmed) {
            $.ajax({
                type: 'POST',
                url: '/admin-panel/maintenance/delete-document/',
                data: {
                    url: imageUrl,
                    maintenance_id: maintenanceId
                },
                success: function(response) {
                    if (response.status === 'success') {
                        Swal.fire('حذف شد!', 'تصویر با موفقیت حذف شد.', 'success');
                        button.closest('.image-item').remove();
                    } else {
                        Swal.fire('خطا', response.message, 'error');
                    }
                },
                error: function() {
                    Swal.fire('خطا', 'خطا در حذف تصویر', 'error');
                }
            });
        }
    });
});
$(document).on('click', '.edit-maintenance-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#maintenanceForm').attr('action', '/admin-panel/maintenance/edit/' + id + '/');

    $('#id_maintenance_description').val($(this).data('maintenance_description'));
    // Ensure date is in YYYY-MM-DD format before setting it
    var maintenanceStartDate = $(this).data('maintenance_start_date');
    var maintenanceEndDate = $(this).data('maintenance_end_date');
    // If the date is in a format other than YYYY-MM-DD, convert it here
    // You can use moment.js or another library for conversion if necessary
    $('#id_maintenance_start_date').val(maintenanceStartDate);
    $('#id_maintenance_end_date').val(maintenanceEndDate);

    $('#id_maintenance_price').val($(this).data('maintenance_price'));
    $('#id_maintenance_status').val($(this).data('maintenance_status'));
    $('#id_service_company').val($(this).data('service_company'));
    $('#id_maintenance_document_no').val($(this).data('maintenance_document_no'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    $('#exampleModalLongTitle').text('ویرایش سند');
    $('#btn-submit-receive').text('ویرایش سند');
});
 document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('maintenanceForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

// ===================================================

$(document).on('click', '.edit-charge-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#chargeForm').attr('action', '/admin-panel/charge/edit/' + id + '/');

    $('#id_name').val($(this).data('name'));
    $('#id_fix_amount').val($(this).data('fix_amount'));
    $('#id_civil').val($(this).data('civil'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    let chargeName = $(this).data('name');
    $('#exampleModalLongTitle').text('ویرایش : ' + chargeName);
    $('#btn-submit-receive').text('ویرایش شارژ');
});
 document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('chargeForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });
 // ==============================================
$(document).on('click', '.edit-charge-area-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#areaForm').attr('action', '/admin-panel/area/charge/edit/' + id + '/');

    $('#id_name').val($(this).data('name'));
    $('#id_area_amount').val($(this).data('area_amount'));
    $('#id_civil').val($(this).data('civil'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
   let chargeName = $(this).data('name');
    $('#exampleModalLongTitle').text('ویرایش : ' + chargeName);
    $('#btn-submit-receive').text('ویرایش شارژ');
});
 document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('areaForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });


 // ==============================================
$(document).on('click', '.edit-charge-person-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#personForm').attr('action', '/admin-panel/person/charge/edit/' + id + '/');

    $('#id_name').val($(this).data('name'));
    $('#id_person_amount').val($(this).data('person_amount'));
    $('#id_civil').val($(this).data('civil'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    let chargeName = $(this).data('name');
    $('#exampleModalLongTitle').text('ویرایش : ' + chargeName);
    $('#btn-submit-receive').text('ویرایش شارژ');
});
 document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('personForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

 // ==============================================
// When the Edit button is clicked
$(document).on('click', '.edit-fix-area-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#fixAreaForm').attr('action', '/admin-panel/fix/area/charge/edit/' + id + '/');

    // Set the form values based on the clicked button's data attributes
    $('#id_charge_name').val($(this).data('charge_name'));
    $('#id_area_amount').val($(this).data('area_amount'));
    $('#id_fix_charge').val($(this).data('fix_charge'));
    $('#id_civil_charge').val($(this).data('civil_charge'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    let chargeName = $(this).data('charge_name');
    $('#exampleModalLongTitle').text('ویرایش شارژ: ' + chargeName);
    $('#btn-submit-receive').text('ویرایش شارژ');
});

  document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('fixAreaForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

// ============================================================

 // ==============================================
// When the Edit button is clicked
$(document).on('click', '.edit-fix-person-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#fixPersonForm').attr('action', '/admin-panel/fix/person/charge/edit/' + id + '/');

    // Set the form values based on the clicked button's data attributes
    $('#id_charge_name').val($(this).data('charge_name'));
    $('#id_person_amount').val($(this).data('person_amount'));
    $('#id_fix_charge').val($(this).data('fix_charge'));
    $('#id_civil_charge').val($(this).data('civil_charge'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    let chargeName = $(this).data('charge_name');
    $('#exampleModalLongTitle').text('ویرایش شارژ: ' + chargeName);
    $('#btn-submit-receive').text('ویرایش شارژ');
});

  document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('fixPersonForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

// ============================================================
$(document).on('click', '.edit-area-person-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#persianAreaForm').attr('action', '/admin-panel/area/person/charge/edit/' + id + '/');

    // Set the form values based on the clicked button's data attributes
    $('#id_charge_name').val($(this).data('charge_name'));
    $('#id_person_charge').val($(this).data('person_charge'));
    $('#id_area_charge').val($(this).data('area_charge'));
    $('#id_civil_charge').val($(this).data('civil_charge'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    let chargeName = $(this).data('charge_name');
    $('#exampleModalLongTitle').text('ویرایش شارژ: ' + chargeName);
    $('#btn-submit-receive').text('ویرایش شارژ');
});

  document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('persianAreaForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

// ============================================================

$(document).on('click', '.edit-area-person-fix-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#persianAreaForm').attr('action', '/admin-panel/fix/area/person/charge/edit/' + id + '/');

    // Set the form values based on the clicked button's data attributes
    $('#id_charge_name').val($(this).data('charge_name'));
    $('#id_fix_charge').val($(this).data('fix_charge'));
    $('#id_person_charge').val($(this).data('person_charge'));
    $('#id_area_charge').val($(this).data('area_charge'));
    $('#id_civil_charge').val($(this).data('civil_charge'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    let chargeName = $(this).data('charge_name');
    $('#exampleModalLongTitle').text('ویرایش شارژ: ' + chargeName);
    $('#btn-submit-receive').text('ویرایش شارژ');
});

  document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('persianAreaFixForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });

// ============================================================
$(document).on('click', '.edit-variable-fix-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#variableFixForm').attr('action', '/admin-panel/fix/variable/charge/edit/' + id + '/');

    // Set the form values based on the clicked button's data attributes
    $('#id_charge_name').val($(this).data('charge_name'));
    $('#id_salary').val($(this).data('salary'));
    $('#id_elevator_cost').val($(this).data('elevator_cost'));
    $('#id_public_electricity').val($(this).data('public_electricity'));
    $('#id_common_expenses').val($(this).data('common_expenses'));
    $('#id_facility_cost').val($(this).data('facility_cost'));
    $('#id_camera_cost').val($(this).data('camera_cost'));
    $('#id_office_cost').val($(this).data('office_cost'));
    $('#id_insurance_cost').val($(this).data('insurance_cost'));
    $('#id_extinguished_cost').val($(this).data('extinguished_cost'));
    $('#id_green_space_cost').val($(this).data('green_space_cost'));
    $('#id_public_water').val($(this).data('public_water'));
    $('#id_public_gas').val($(this).data('public_gas'));
    $('#id_civil_charge').val($(this).data('civil_charge'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    let chargeName = $(this).data('charge_name');
    $('#exampleModalLongTitle').text('ویرایش شارژ: ' + chargeName);
    $('#btn-submit-receive').text('ویرایش شارژ');
});

  document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong');
    const form = document.getElementById('variableFixForm');

    modal.addEventListener('hidden.bs.modal', function () {
      form.reset();
    });
  });
  // =======================================================
    document.addEventListener('DOMContentLoaded', function () {
        const toggleBtn = document.getElementById('toggle-select-btn');
        let allSelected = false;

        toggleBtn.addEventListener('click', function () {
            const checkboxes = document.querySelectorAll('.unit-checkbox:not(:disabled)');
            checkboxes.forEach(cb => cb.checked = !allSelected);

            allSelected = !allSelected;
            toggleBtn.textContent = allSelected ? 'لغو انتخاب همه واحدها' : 'انتخاب همه واحدها';
        });
    });

// ============================================
function confirmDeleteWithSweetAlert(event) {
    event.preventDefault(); // جلوگیری از رفتن به لینک فوری

    const url = event.currentTarget.href; // آدرس لینک

    Swal.fire({
        title: 'آیا نسبت به حذف این آیتم اطمینان دارید؟',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'بله',
        cancelButtonText: 'خیر',
        reverseButtons: true
    }).then((result) => {
        if (result.isConfirmed) {
            // اگر کاربر تأیید کرد، به لینک هدایت شود
            window.location.href = url;
        }
        // اگر لغو کرد، کاری انجام نمی‌شود
    });

    return false; // جلوگیری از رفتار پیش‌فرض لینک
}

