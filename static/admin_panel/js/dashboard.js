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
                    <button type="button" class="btn btn-sm btn-danger delete-image-btn"
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



$(document).on('click', '.delete-image-btn', function () {
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
                    <button type="button" class="btn btn-sm btn-danger delete-image-btn"
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

$(document).on('click', '.delete-image-btn', function () {
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