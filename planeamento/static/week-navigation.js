(function () {
    function isoWeekToDate(weekValue) {
        var match = /^([0-9]{4})-W([0-9]{2})$/.exec(weekValue);
        if (!match) {
            return null;
        }
        var year = Number(match[1]);
        var week = Number(match[2]);
        if (!year || !week) {
            return null;
        }
        var fourthJan = new Date(Date.UTC(year, 0, 4));
        var dayOfWeek = fourthJan.getUTCDay();
        if (dayOfWeek === 0) {
            dayOfWeek = 7;
        }
        var isoWeekStart = new Date(fourthJan);
        isoWeekStart.setUTCDate(fourthJan.getUTCDate() - (dayOfWeek - 1) + (week - 1) * 7);
        return isoWeekStart;
    }

    function dateToIsoWeek(date) {
        var target = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
        var dayNumber = target.getUTCDay();
        if (dayNumber === 0) {
            dayNumber = 7;
        }
        target.setUTCDate(target.getUTCDate() + 4 - dayNumber);
        var yearStart = new Date(Date.UTC(target.getUTCFullYear(), 0, 1));
        var diffInDays = Math.floor((target - yearStart) / 86400000) + 1;
        var weekNumber = Math.ceil(diffInDays / 7);
        var isoYear = target.getUTCFullYear();
        var paddedWeek = weekNumber < 10 ? "0" + weekNumber : String(weekNumber);
        return isoYear + "-W" + paddedWeek;
    }

    function shiftWeekValue(currentWeek, offsetWeeks) {
        var startDate = isoWeekToDate(currentWeek);
        if (!startDate) {
            return null;
        }
        startDate.setUTCDate(startDate.getUTCDate() + offsetWeeks * 7);
        return dateToIsoWeek(startDate);
    }

    function dispatchUpdates(input) {
        var changeEvent = new Event("change", { bubbles: true });
        var inputEvent = new Event("input", { bubbles: true });
        input.dispatchEvent(inputEvent);
        input.dispatchEvent(changeEvent);
    }

    document.addEventListener("DOMContentLoaded", function () {
        var navigations = document.querySelectorAll("[data-week-navigation]");
        if (!navigations.length) {
            return;
        }
        Array.prototype.forEach.call(navigations, function (navigation) {
            var weekInput = navigation.querySelector('input[type="week"]');
            if (!weekInput) {
                return;
            }
            navigation.addEventListener("click", function (event) {
                var button = event.target.closest("[data-week-nav]");
                if (!button || !navigation.contains(button)) {
                    return;
                }
                event.preventDefault();
                var currentValue = weekInput.value || weekInput.dataset.defaultWeek || "";
                if (!currentValue) {
                    return;
                }
                var direction = button.getAttribute("data-week-nav");
                var offset = 0;
                if (direction === "next") {
                    offset = 1;
                } else if (direction === "prev") {
                    offset = -1;
                } else {
                    return;
                }
                var nextWeek = shiftWeekValue(currentValue, offset);
                if (!nextWeek || nextWeek === weekInput.value) {
                    return;
                }
                weekInput.value = nextWeek;
                dispatchUpdates(weekInput);
            });
        });
    });
})();
