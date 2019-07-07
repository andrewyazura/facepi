document.addEventListener('DOMContentLoaded', function () {
    let elems = document.querySelectorAll('.sidenav');
    let instances = M.Sidenav.init(elems);
});

document.addEventListener('DOMContentLoaded', function () {
    let elems = document.querySelectorAll('select');
    let instances = M.FormSelect.init(elems);
});
