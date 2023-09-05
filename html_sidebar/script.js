function showContent(id) {
    const contents = document.querySelectorAll('.content');
    contents.forEach(content => {
        content.style.display = 'none';
    });
    document.getElementById(id).style.display = 'block';
}

function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar.style.width === '50px') {
        sidebar.style.width = '100px';
    } else {
        sidebar.style.width = '50px';
    }
}
