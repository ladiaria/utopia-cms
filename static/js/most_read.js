var section_masleidos = window.document.getElementById('mas-leidos-content');
if(section_masleidos){
    var xhttp = new XMLHttpRequest();
    // Making our connection
    var url = section_masleidos.getAttribute('data-url');
    xhttp.open("GET", url, true);

    // function execute after request is successful
    xhttp.onreadystatechange = function () {
      if (this.readyState == 4 && this.status == 200) {
          section_masleidos.innerHTML = this.responseText;
      }
    }
    // Sending our request
    xhttp.send();
}
