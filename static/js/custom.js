function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        let cookies = document.cookie.split(';');
        for (let i=0; i<cookies.length; i++){
            let cookie = cookies[i].trim();
            if(cookie.substring(0,name.length+1) === (name+'=')){
                cookieValue = decodeURIComponent(cookie.substring(name.length+1));
                break;
            }
        }
    }
    return cookieValue;
}

var csrftoken = getCookie('csrftoken');

// باز کردن modal و پر کردن فرم + نمایش تصاویر
$(document).on('click', '.edit-user-pay', function() {
    let button = $(this);
    let payId = button.data('pay-id');
    let images = button.data('images') || [];

    // فرم
    $('#id_pay_id').val(payId);
    $('#id_amount').val(button.data('amount'));
    $('#id_register_date').val(button.data('register_date'));
    $('#id_description').val(button.data('description'));
    $('#id_details').val(button.data('details'));

    // action فرم
    $('#userPayForm').attr('action', '/pay/user/edit/' + payId + '/');

    // تصاویر
    $('#preview').empty();
    if(images.length > 0){
        images.forEach(function(url){
            let wrapper = `
                <div class="image-item m-2 position-relative" style="display:inline-block;">
                    <img src="${url}" style="width:100px;height:100px;object-fit:cover;border:1px solid #ccc;">
                    <button type="button" class="btn btn-sm btn-danger delete-image21-btn"
                            data-url="${url}" data-pay-id="${payId}"
                            style="position:absolute;top:-5px;right:-5px;border-radius:50%;">×</button>
                </div>`;
            $('#preview').append(wrapper);
        });
    } else {
        $('#preview').html('<p>تصویری وجود ندارد.</p>');
    }

    // متن modal
    $('#exampleModalLongTitle2').text('ویرایش پرداخت');
    $('#btn-submit-expense').text('ویرایش پرداخت');
});

// حذف تصویر
$(document).on('click', '.delete-image21-btn', function(){
    let button = $(this);
    let imageUrl = button.data('url');
    let payId = button.data('pay-id');

    if(!imageUrl || !payId){
        Swal.fire('خطا', 'URL یا ID پرداخت مشخص نیست', 'error');
        return;
    }

    Swal.fire({
        title:'آیا مطمئنی حذف شود؟',
        icon:'warning',
        showCancelButton:true,
        confirmButtonText:'بله',
        cancelButtonText:'لغو'
    }).then((result)=>{
        if(result.isConfirmed){
            $.ajax({
                type:'POST',
                url:'/user/pay/delete-document/',
                data:{ url: imageUrl, pay_id: payId },
                headers:{ 'X-CSRFToken': csrftoken },
                success:function(resp){
                    if(resp.status === 'success'){
                        button.closest('.image-item').remove();
                        Swal.fire('حذف شد','تصویر با موفقیت حذف شد','success');
                    } else {
                        Swal.fire('خطا', resp.message,'error');
                    }
                },
                error:function(){
                    Swal.fire('خطا','خطا در حذف تصویر','error');
                }
            });
        }
    });
});

// reset فرم هنگام بستن modal
document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('exampleModalLong2');
    const form = document.getElementById('userPayForm');

    modal.addEventListener('hidden.bs.modal', function () {
        form.reset();
        $('#preview').empty();
    });
});

function searchTableIncome() {
  var input = document.getElementById("searchInput");
  var filter = input.value.toLowerCase().replace(/,/g, '').replace(/\s/g, '');
  var table = document.getElementById("incomeTable");
  var rows = table.getElementsByTagName("tr");

  for (var i = 1; i < rows.length; i++) {
    var row = rows[i];
    var text = row.innerText.toLowerCase().replace(/,/g, '').replace(/\s/g, '');
    row.style.display = text.includes(filter) ? "" : "none";
  }
}
function openQuery() {
    var form = document.getElementById('query-form');
    form.style.display = (form.style.display === 'none') ? 'block' : 'none';
}
