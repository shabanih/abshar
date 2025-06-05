    function toggleRenterFields() {
    const isOwner = document.getElementById('id_is_owner').value;
    const renterFields = document.getElementById('renter_div');

    if (isOwner === 'True') {
        renterFields.style.display = 'block';  // show fields when user is the owner
    } else {
        renterFields.style.display = 'none';  // hide otherwise (False or not selected)
    }
}

document.addEventListener('DOMContentLoaded', function () {
    toggleRenterFields();
    document.getElementById('id_is_owner').addEventListener('change', toggleRenterFields);
});


document.querySelector('input[name="document"]').addEventListener('change', function (event) {
    const preview = document.getElementById('preview');
    preview.innerHTML = '';

    for (let file of event.target.files) {
        const reader = new FileReader();
        reader.onload = function (e) {
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


$(document).ready(function () {
    $("#from_date, #to_date").persianDatepicker({
        format: 'YYYY-MM-DD',
        autoClose: true,
        initialValue: false,
        observer: true, // Fix positioning
        responsive: true, // (some forks support it, safe to include) autoClose: true,
    });
});

function openQuery() {
    var form = document.getElementById('query-form');
    form.style.display = (form.style.display === 'none') ? 'block' : 'none';
}


function searchTable() {
  var input = document.getElementById("searchInput");
  var filter = input.value.toLowerCase().replace(/,/g, '').replace(/\s/g, '');
  var table = document.getElementById("expenseTable");
  var rows = table.getElementsByTagName("tr");

  for (var i = 1; i < rows.length; i++) {
    var row = rows[i];
    var text = row.innerText.toLowerCase().replace(/,/g, '').replace(/\s/g, '');
    row.style.display = text.includes(filter) ? "" : "none";
  }
}

// ==================================
$(document).on('click', '.edit-income-btn', function () {
    console.log('ویرایش کلیک شد');

    // Get the expense ID from the clicked button's data attributes
    var id = $(this).data('id');
    // Set the form action URL dynamically
    $('#incomeForm').attr('action', '/admin-panel/income/edit/' + id + '/');

    // Populate the form with the expense data
    $('#id_category').val($(this).data('category')).trigger('change');
    $('#id_amount').val($(this).data('amount'));

    // Ensure date is in YYYY-MM-DD format before setting it
    var expenseDate = $(this).data('doc_date');
    // If the date is in a format other than YYYY-MM-DD, convert it here
    // You can use moment.js or another library for conversion if necessary
    $('#id_doc_date').val(expenseDate);  // Assuming it's already in correct format

    $('#id_doc_number').val($(this).data('doc_number'));
    $('#id_description').val($(this).data('description'));
    $('#id_details').val($(this).data('details'));

    // Update the modal title and submit button text for editing
    $('#exampleModalLongTitle2').text('ویرایش درآمد');
    $('#btn-submit-expense').text('ویرایش درآمد');
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
// ==============================================
function searchTableUnit() {
  var input = document.getElementById("searchInput");
  var filter = input.value.toLowerCase().replace(/,/g, '').replace(/\s/g, '');
  var table = document.getElementById("unitTable");
  var rows = table.getElementsByTagName("tr");

  for (var i = 1; i < rows.length; i++) {
    var row = rows[i];
    var text = row.innerText.toLowerCase().replace(/,/g, '').replace(/\s/g, '');
    row.style.display = text.includes(filter) ? "" : "none";
  }
}
// ===========================================================
    function searchTable() {
  var input = document.getElementById("searchInput");
  var filter = input.value.toLowerCase().replace(/,/g, '').replace(/\s/g, '');
  var table = document.getElementById("expenseTable");
  var rows = table.getElementsByTagName("tr");

  for (var i = 1; i < rows.length; i++) {
    var row = rows[i];
    var text = row.innerText.toLowerCase().replace(/,/g, '').replace(/\s/g, '');
    row.style.display = text.includes(filter) ? "" : "none";
  }
}
// ===================================================
    function searchChargeTable() {
    const input = document.getElementById('searchInput');
    const filter = input.value.toLowerCase();
    const cards = document.querySelectorAll('.fixChargeTable');

    cards.forEach(card => {
        const unitTitle = card.querySelector('.card-middleCharge-title').innerText.toLowerCase();
        const cardText = card.querySelector('.card-middleCharge-text').innerText.toLowerCase();

        if (unitTitle.includes(filter) || cardText.includes(filter)) {
            card.parentElement.style.display = '';  // کارت اصلی که col است را نشان بده
        } else {
            card.parentElement.style.display = 'none'; // کارت را مخفی کن
        }
    });
}
