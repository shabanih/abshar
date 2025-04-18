jalaliDatepicker.startWatch({
            minDate: "attr",
            maxDate: "attr",
            minTime: "attr",
            maxTime: "attr",
            dateFormat: "mm-dd-yy",
            hideAfterChange: true,
            autoHide: true,
            showTodayBtn: true,
            showEmptyBtn: true,
            topSpace: 10,
            bottomSpace: 30,
    dayRendering: function (opt, input) {
        return {
            isHollyDay: opt.day === 1,
            dateFormat: "yy-mm-dd",
        }
    }
});

        document.getElementById("aaa").addEventListener("jdp:change",
            function (e) {
                console.log(e)
            });

