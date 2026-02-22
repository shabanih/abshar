// $(function () {
//     /* ChartJS
//      * -------
//      * Data and config for chartjs
//      */
//     'use strict';
//     var data = {
//         labels: ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
//             "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"],
//         datasets: [{
//             label: '# of Votes',
//             data: [10, 19, 3, 5, 2, 3],
//             backgroundColor: [
//                 'rgba(255, 99, 132, 0.2)',
//                 'rgba(54, 162, 235, 0.2)',
//                 'rgba(255, 206, 86, 0.2)',
//                 'rgba(75, 192, 192, 0.2)',
//                 'rgba(153, 102, 255, 0.2)',
//                 'rgba(255, 159, 64, 0.2)'
//             ],
//             borderColor: [
//                 'rgba(255,99,132,1)',
//                 'rgba(54, 162, 235, 1)',
//                 'rgba(255, 206, 86, 1)',
//                 'rgba(75, 192, 192, 1)',
//                 'rgba(153, 102, 255, 1)',
//                 'rgba(255, 159, 64, 1)'
//             ],
//             borderWidth: 1,
//             fill: false,
//
//         }]
//     };
//     var multiLineData = {
//         labels: ["Red", "Blue", "Yellow", "Green", "Purple", "Orange"],
//         datasets: [{
//             label: 'Dataset 1',
//             data: [12, 19, 3, 5, 2, 3],
//             borderColor: [
//                 '#587ce4'
//             ],
//             borderWidth: 2,
//             fill: false
//         },
//             {
//                 label: 'Dataset 2',
//                 data: [5, 23, 7, 12, 42, 23],
//                 borderColor: [
//                     '#ede190'
//                 ],
//                 borderWidth: 2,
//                 fill: false
//             },
//             {
//                 label: 'Dataset 3',
//                 data: [15, 10, 21, 32, 12, 33],
//                 borderColor: [
//                     '#f44252'
//                 ],
//                 borderWidth: 2,
//                 fill: false
//             }
//         ]
//     };
//     var options = {
//         scales: {
//             y: {
//                 ticks: {
//                     beginAtZero: true
//                 }
//             }
//         },
//         legend: {
//             display: false
//         },
//         elements: {
//             line: {
//                 tension: 0.5
//             },
//             point: {
//                 radius: 0
//             }
//         }
//
//     };
//     var doughnutPieData = {
//         labels: ['مستاجر', 'مالک', 'خالی'],
//         datasets: [{
//             data: [
//                 ownerRenterStats.renter,
//                 ownerRenterStats.owner,
//                 ownerRenterStats.empty
//             ],
//             backgroundColor: [
//                 'rgba(54, 162, 235, 0.6)',   // مستاجر (آبی)
//                 'rgba(75, 192, 192, 0.6)',   // مالک (سبز)
//                 'rgba(255, 159, 64, 0.6)'    // خالی (نارنجی)
//             ],
//             borderWidth: 1
//         }]
//     };
//     console.log(residenceStats.occupied, residenceStats.empty);
//     var pieData = {
//         labels: ['ساکن', 'خالی'],
//         datasets: [{
//             data: [residenceStats.occupied, residenceStats.empty],
//             backgroundColor: [
//                 'rgba(54, 162, 235, 0.5)',
//                 'rgba(255, 99, 132, 0.5)',
//                 // 'rgba(255, 206, 86, 0.5)',
//                 // 'rgba(75, 192, 192, 0.5)',
//                 // 'rgba(153, 102, 255, 0.5)',
//                 // 'rgba(255, 159, 64, 0.5)'
//             ],
//             // borderColor: ['#28a745', '#dc3545'],
//             borderWidth: 1
//         }]
//     };
//     var doughnutPieOptions = {
//         responsive: true,
//         animation: {
//             animateScale: true,
//             animateRotate: true
//         }
//     };
//     var areaData = {
//         labels: ["2013", "2014", "2015", "2016", "2017"],
//         datasets: [{
//             label: '# of Votes',
//             data: [12, 19, 3, 5, 2, 3],
//             backgroundColor: [
//                 'rgba(255, 99, 132, 0.2)',
//                 'rgba(54, 162, 235, 0.2)',
//                 'rgba(255, 206, 86, 0.2)',
//                 'rgba(75, 192, 192, 0.2)',
//                 'rgba(153, 102, 255, 0.2)',
//                 'rgba(255, 159, 64, 0.2)'
//             ],
//             borderColor: [
//                 'rgba(255,99,132,1)',
//                 'rgba(54, 162, 235, 1)',
//                 'rgba(255, 206, 86, 1)',
//                 'rgba(75, 192, 192, 1)',
//                 'rgba(153, 102, 255, 1)',
//                 'rgba(255, 159, 64, 1)'
//             ],
//             borderWidth: 1,
//             fill: true, // 3: no fill
//         }]
//     };
//     var areaOptions = {
//         elements: {
//             line: {
//                 tension: 0.5
//             }
//         },
//         plugins: {
//             filler: {
//                 propagate: true
//             }
//         }
//     }
//     var multiAreaData = {
//         labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
//         datasets: [{
//             label: 'Facebook',
//             data: [8, 11, 13, 15, 12, 13, 16, 15, 13, 19, 11, 14],
//             borderColor: ['rgba(255, 99, 132, 0.5)'],
//             backgroundColor: ['rgba(255, 99, 132, 0.5)'],
//             borderWidth: 1,
//             fill: true
//         },
//             {
//                 label: 'Twitter',
//                 data: [7, 17, 12, 16, 14, 18, 16, 12, 15, 11, 13, 9],
//                 borderColor: ['rgba(54, 162, 235, 0.5)'],
//                 backgroundColor: ['rgba(54, 162, 235, 0.5)'],
//                 borderWidth: 1,
//                 fill: true
//             },
//             {
//                 label: 'Linkedin',
//                 data: [6, 14, 16, 20, 12, 18, 15, 12, 17, 19, 15, 11],
//                 borderColor: ['rgba(255, 206, 86, 0.5)'],
//                 backgroundColor: ['rgba(255, 206, 86, 0.5)'],
//                 borderWidth: 1,
//                 fill: true
//             }
//         ]
//     };
//     var multiAreaOptions = {
//         plugins: {
//             filler: {
//                 propagate: true
//             }
//         },
//         elements: {
//             line: {
//                 tension: 0.5
//             },
//             point: {
//                 radius: 0
//             }
//         },
//         scales: {
//             x: {
//                 gridLines: {
//                     display: false
//                 }
//             },
//             y: {
//                 gridLines: {
//                     display: false
//                 }
//             }
//         }
//     }
//
//     var scatterChartData = {
//         datasets: [{
//             label: 'First Dataset',
//             data: [{
//                 x: -10,
//                 y: 0
//             },
//                 {
//                     x: 0,
//                     y: 3
//                 },
//                 {
//                     x: -25,
//                     y: 5
//                 },
//                 {
//                     x: 40,
//                     y: 5
//                 }
//             ],
//             backgroundColor: [
//                 'rgba(255, 99, 132, 0.2)'
//             ],
//             borderColor: [
//                 'rgba(255,99,132,1)'
//             ],
//             borderWidth: 1
//         },
//             {
//                 label: 'Second Dataset',
//                 data: [{
//                     x: 10,
//                     y: 5
//                 },
//                     {
//                         x: 20,
//                         y: -30
//                     },
//                     {
//                         x: -25,
//                         y: 15
//                     },
//                     {
//                         x: -10,
//                         y: 5
//                     }
//                 ],
//                 backgroundColor: [
//                     'rgba(54, 162, 235, 0.2)',
//                 ],
//                 borderColor: [
//                     'rgba(54, 162, 235, 1)',
//                 ],
//                 borderWidth: 1
//             }
//         ]
//     }
//
//     var scatterChartOptions = {
//         scales: {
//             x: {
//                 type: 'linear',
//                 position: 'bottom'
//             }
//         }
//     }
//     // Get context with jQuery - using jQuery's .get() method.
//
//     // if ($("#barChart").length) {
//     //   var barChartCanvas = $("#barChart").get(0).getContext("2d");
//     //   // This will get the first returned node in the jQuery collection.
//     //   var barChart = new Chart(barChartCanvas, {
//     //     type: 'bar',
//     //     data: data,
//     //     options: options
//     //   });
//     // }
//
//     if (document.getElementById('doughnutChart')) {
//         var ctx = document.getElementById('doughnutChart').getContext('2d');
//         new Chart(ctx, {
//             type: 'doughnut',
//             data: doughnutPieData,
//             options: doughnutPieOptions
//         });
//     }
//
//
//     if (document.getElementById('pieChart')) {
//         var cty = document.getElementById('pieChart').getContext('2d');
//         new Chart(cty, {
//             type: 'pie',
//             data: pieData,
//             options: doughnutPieOptions
//         });
//     }
//
//
//     if ($("#areaChart").length) {
//         var areaChartCanvas = $("#areaChart").get(0).getContext("2d");
//         var areaChart = new Chart(areaChartCanvas, {
//             type: 'line',
//             data: areaData,
//             options: areaOptions
//         });
//     }
//
// });

// ============================================================
window.addEventListener("DOMContentLoaded", function () {

    const persianMonthNames = [
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
    ];

    const monthSelect = document.getElementById("monthSelect");
    const yearSelect = document.getElementById("yearSelect");
    const prevBtn = document.getElementById("prevMonthBtn");
    const nextBtn = document.getElementById("nextMonthBtn");
    const todayBtn = document.getElementById("gotoTodayBtn");

    const noteModal = document.getElementById("noteModal");
    const noteText = document.getElementById("noteText");
    const selectedDayTitle = document.getElementById("selectedDayTitle");
    const saveNoteBtn = document.getElementById("saveNoteBtn");
    const closeNoteBtn = document.getElementById("closeNoteBtn");
    const deleteNoteBtn = document.getElementById("deleteNoteBtn");

    let selectedYear, selectedMonth, selectedDay;

    const todayParts = new Intl.DateTimeFormat("fa-IR-u-nu-latn", {
        year: "numeric", month: "numeric", day: "numeric", calendar: "persian"
    }).formatToParts(new Date());

    let currentYear = parseInt(todayParts.find(p => p.type === "year").value);
    let currentMonth = parseInt(todayParts.find(p => p.type === "month").value);
    let currentDay = parseInt(todayParts.find(p => p.type === "day").value);

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

    const csrftoken = getCookie('csrftoken');

    // سلکت‌ها
    persianMonthNames.forEach((name, i) => {
        monthSelect.appendChild(new Option(name, i + 1));
    });
    for (let y = currentYear - 5; y <= currentYear + 5; y++) {
        yearSelect.appendChild(new Option(y, y));
    }
    monthSelect.value = currentMonth;
    yearSelect.value = currentYear;

    async function renderCalendar() {
        const tbody = document.querySelector("#calendar tbody");
        tbody.innerHTML = "";

        // گرفتن نوت‌ها از سرور
        let notes = {};
        try {
            const res = await fetch(`/admin-panel/calendar/notes/${currentYear}/${currentMonth}/`);
            notes = await res.json();
            console.log("Notes from server:", notes);
        } catch (e) {
            console.error(e);
        }

        const daysInMonth = new Date(currentYear, currentMonth <= 6 ? currentMonth : currentMonth + 1, 0).getDate();
        const firstDayGregorian = new Date(currentYear, currentMonth - 1, 1);
        const weekDay = firstDayGregorian.getDay();


        let row = document.createElement("tr");
        for (let i = 0; i < weekDay; i++) {
            row.appendChild(document.createElement("td"));
        }

        for (let d = 1; d <= daysInMonth; d++) {
            if (row.children.length === 7) {
                tbody.appendChild(row);
                row = document.createElement("tr");
            }

            const td = document.createElement("td");
            td.textContent = d;

            const noteKey = String(d);

            if (notes[noteKey]) {
                td.classList.add("has-note");

                // اضافه کردن پیش‌نمایش نوت
                const preview = document.createElement("div");
                preview.classList.add("note-preview");
                // نمایش فقط 8 کاراکتر اول
                preview.textContent = notes[noteKey].length > 13 ? notes[noteKey].substring(0, 8) + "…" : notes[noteKey];
                td.appendChild(preview);
            }

            // if(d===currentDay && currentMonth===parseInt(todayParts.find(p=>p.type==='month').value)
            //    && currentYear===parseInt(todayParts.find(p=>p.type==='year').value)){
            //     td.classList.add("today");
            // }
            if (
                d === currentDay &&
                currentMonth === parseInt(todayParts.find(p => p.type === 'month').value) &&
                currentYear === parseInt(todayParts.find(p => p.type === 'year').value)
            ) {
                td.classList.add("today");

                // اگر امروز نوت نداشت، "یادداشت کن" نمایش بده
                if (!notes[noteKey]) {
                    const addNote = document.createElement("div");
                    addNote.classList.add("add-note-today");
                    addNote.textContent = "یادداشت کن";

                    addNote.onclick = function (e) {
                        e.stopPropagation(); // جلوگیری از اجرای onclick اصلی td
                        selectedYear = currentYear;
                        selectedMonth = currentMonth;
                        selectedDay = d;
                        selectedDayTitle.textContent = `یادداشت ${d} ${persianMonthNames[currentMonth - 1]}`;
                        noteText.value = "";
                        noteModal.style.display = "flex";
                    };

                    td.appendChild(addNote);
                }
            }

            td.onclick = () => {
                selectedYear = currentYear;
                selectedMonth = currentMonth;
                selectedDay = d;
                selectedDayTitle.textContent = `یادداشت ${d} ${persianMonthNames[currentMonth - 1]}`;
                noteText.value = notes[noteKey] || "";
                noteModal.style.display = "flex";
            };

            row.appendChild(td);
        }


        if (row.children.length > 0) tbody.appendChild(row);
    }

    function saveNote() {
        const noteValue = noteText.value.trim();
        fetch('/admin-panel/calendar/save-note/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrftoken},
            body: JSON.stringify({year: selectedYear, month: selectedMonth, day: selectedDay, note: noteValue})
        }).then(() => {
            noteModal.style.display = "none";
            renderCalendar();
        });
    }

    function deleteNote() {
        fetch('/admin-panel/calendar/delete-note/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrftoken},
            body: JSON.stringify({year: selectedYear, month: selectedMonth, day: selectedDay})
        }).then(() => {
            noteModal.style.display = "none";
            renderCalendar();
        });
    }

    saveNoteBtn.addEventListener("click", saveNote);
    deleteNoteBtn.addEventListener("click", deleteNote);
    closeNoteBtn.addEventListener("click", () => {
        noteModal.style.display = "none";
    });

    prevBtn.addEventListener("click", () => {
        currentMonth--;
        if (currentMonth < 1) {
            currentMonth = 12;
            currentYear--;
        }
        monthSelect.value = currentMonth;
        yearSelect.value = currentYear;
        renderCalendar();
    });
    nextBtn.addEventListener("click", () => {
        currentMonth++;
        if (currentMonth > 12) {
            currentMonth = 1;
            currentYear++;
        }
        monthSelect.value = currentMonth;
        yearSelect.value = currentYear;
        renderCalendar();
    });
    todayBtn.addEventListener("click", () => {
        currentYear = parseInt(todayParts.find(p => p.type === 'year').value);
        currentMonth = parseInt(todayParts.find(p => p.type === 'month').value);
        monthSelect.value = currentMonth;
        yearSelect.value = currentYear;
        renderCalendar();
    });
    monthSelect.addEventListener("change", () => {
        currentMonth = parseInt(monthSelect.value);
        renderCalendar();
    });
    yearSelect.addEventListener("change", () => {
        currentYear = parseInt(yearSelect.value);
        renderCalendar();
    });

    renderCalendar();
});


// =========================================

var months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];

var chartColors = {
    red: 'rgb(255, 99, 132)',
    blue: 'rgb(54, 162, 235)'
};

var barData = {
    labels: months,
    datasets: [
        {
            label: 'پرداخت شده',
            backgroundColor: Chart.helpers.color(chartColors.blue).alpha(0.5).rgbString(),
            borderColor: chartColors.blue,
            borderWidth: 1,
            data: paidCharges
        },
        {
            label: 'پرداخت نشده',
            backgroundColor: Chart.helpers.color(chartColors.red).alpha(0.5).rgbString(),
            borderColor: chartColors.red,
            borderWidth: 1,
            data: unpaidCharges
        }
    ]
};

var ctx = document.getElementById("barChart").getContext("2d");
var myNewChartB = new Chart(ctx, {
    type: 'bar',
    data: barData,
    options: {
        responsive: true,
        maintainAspectRatio: true, // حفظ نسبت تصویر
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    font: {family: 'Vazir', size: 14}
                }
            },
            title: {
                display: true,
                text: 'وضعیت شارژ ماهانه2',
                font: {family: 'Vazir', size: 25, weight: 'bold'}
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    font: {family: 'Vazir', size: 12},
                    stepSize: 50,
                    // برای نمایش اعداد فارسی
                    callback: function (value) {
                        const persianDigits = "۰۱۲۳۴۵۶۷۸۹";
                        return value.toString().replace(/\d/g, d => persianDigits[d]);
                    }
                }
            },
            x: {
                ticks: {font: {family: 'Vazir', size: 12}}
            }
        }
    }
});


document.addEventListener("DOMContentLoaded", function () {

    const ownerRenterStats = JSON.parse(
        document.getElementById("owner_renter_json").textContent
    );

    const ctx = document.getElementById('doughnutChart').getContext('2d');

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['مستاجر', 'مالک', 'خالی'],
            datasets: [{
                data: [
                    ownerRenterStats.renter || 0,
                    ownerRenterStats.owner || 0,
                    ownerRenterStats.empty || 0
                ],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.7)',   // مستاجر
                    'rgba(75, 192, 192, 0.7)',   // مالک
                    'rgba(255, 99, 132, 0.5)',   // خالی
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            animation: {
                animateScale: true,
                animateRotate: true
            }


        }
    });

});

// ======

document.addEventListener("DOMContentLoaded", function () {

    const expenseData = JSON.parse(
        document.getElementById("expense_chart_json").textContent
    );

    const ctx = document.getElementById('expenseChart').getContext('2d');

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: expenseData.labels,
            datasets: [{
                data: expenseData.data,
                backgroundColor: [
                    '#4CAF50',
                    '#2196F3',
                    '#FF9800',
                    '#9C27B0',
                    '#F44336',
                    '#00BCD4',
                    '#8BC34A'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let value = context.raw.toLocaleString();
                            return context.label + ' : ' + value + ' تومان';
                        }
                    }
                }
            }
        }
    });

});



document.addEventListener("DOMContentLoaded", function () {

    const incomeData = JSON.parse(
    document.getElementById("income_chart_json").textContent
    );

    const ctx = document.getElementById('incomeChart').getContext('2d');

    new Chart(ctx, {
    type: 'doughnut',
    data: {
    labels: incomeData.labels,
    datasets: [{
    data: incomeData.data,
    backgroundColor: [
    '#28a745',
    '#17a2b8',
    '#ffc107',
    '#6610f2',
    '#e83e8c',
    '#20c997'
    ],
    borderWidth: 1
}]
},
    options: {
    responsive: true,
    plugins: {
    legend: {
    position: 'bottom'
},
    tooltip: {
    callbacks: {
    label: function(context) {
    let value = context.raw.toLocaleString();
    return context.label + ' : ' + value + ' تومان';
}
}
}
}
}
});

});
