// document.addEventListener('DOMContentLoaded', function () {
//     const isOwnerField = document.getElementById('id_is_owner');
//     const renterDiv = document.getElementById('renter_div');
//     console.log('ok')
//
//     function toggleRenterFields() {
//         if (isOwnerField.value === 'True') {
//             renterDiv.style.display = 'block';  // Switch to block for layout consistency
//         } else {
//             renterDiv.style.display = 'none';
//         }
//     }
//
//     isOwnerField.addEventListener('change', toggleRenterFields);
//
//     // Run the function on initial load to check the state of the field
//     toggleRenterFields();
// });
//
// // Select all open modal buttons and modal overlays
// const openModalBtns = document.querySelectorAll('.open-modal-btn');
// const closeModalBtns = document.querySelectorAll('.close-modal-btn');
// const modalOverlays = document.querySelectorAll('.modal-overlay');
//
// // Loop through each open modal button
// openModalBtns.forEach((button, index) => {
//   button.addEventListener('click', function () {
//     modalOverlays[index].classList.add('open'); // Show the corresponding modal
//   });
// });
//
// // Loop through each close modal button
// closeModalBtns.forEach((button, index) => {
//   button.addEventListener('click', function () {
//     modalOverlays[index].classList.remove('open'); // Hide the corresponding modal
//   });
// });
//
// // Close modal if clicking outside the modal content
// modalOverlays.forEach((overlay, index) => {
//   overlay.addEventListener('click', function (e) {
//     if (e.target === overlay) {
//       modalOverlays[index].classList.remove('open'); // Close modal if clicking outside
//     }
//   });
// });
//
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('expense-category-form');
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      const formData = new FormData(form);

      fetch("{% url 'add_category' %}", {
        method: 'POST',
        headers: {
          'X-CSRFToken': formData.get('csrfmiddlewaretoken')
        },
        body: formData
      })
      .then(response => {
        if (response.redirected) {
          // مودال دوم رو ببند
          const modal2 = bootstrap.Modal.getInstance(document.getElementById('exampleModalLong2'));
          modal2.hide();

          // مودال اول رو باز کن
          const modal1 = new bootstrap.Modal(document.getElementById('exampleModalLong'));
          modal1.show();

          // رفرش کردن لیست موضوع‌ها (می‌تونی اینجا از AJAX هم استفاده کنی)
          // یا ساده‌ترین حالت: reload کل صفحه (در صورت نیاز)
          location.reload();
        } else {
          return response.text();
        }
      })
      .then(html => {
        // در صورت داشتن ارورهای فرم، آن‌ها را نمایش بده
        document.getElementById('exampleModalLong2').querySelector('.modal-body').innerHTML = html;
      });
    });
  });


  document.addEventListener("DOMContentLoaded", function () {
    const modal1El = document.getElementById('exampleModalLong');    // مودال اول
    const modal2El = document.getElementById('exampleModalLong2');   // مودال دوم

    const modal1 = new bootstrap.Modal(modal1El);
    const modal2 = new bootstrap.Modal(modal2El);

    // وقتی روی دکمه ثبت موضوع کلیک شد، مودال دوم باز شه ولی مودال اول بسته نشه
    document.querySelector(".open-second-modal").addEventListener("click", function () {
      modal2.show();
    });

    // وقتی مودال دوم بسته شد، مودال اول دوباره باز بشه
    modal2El.addEventListener("hidden.bs.modal", function () {
      modal1.show();
    });
  });