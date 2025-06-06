document.addEventListener('DOMContentLoaded', function() {

    function setPerplexityBtnStatus(btn, status=false, text='Enviar a Perplexity'){
        btn.disabled = status;
        btn.innerText = text;
    }
    function formatPerplexityResponse(data) {
        let output = "Metatítulos:\n";
        data.metatitles.forEach((t, i) => {
            output += `${i + 1}. ${t}\n`;
        });
        output += "\nCopys para redes sociales:\n";
        data.copys.forEach((c, i) => {
            output += `${i + 1}. ${c}\n`;
        });
        return output;
    }

//    const questionArea = document.getElementById('id_perplexity_message');
    const continueBtn = document.querySelector('input[type="submit"][name="_continue"]');

    // Create the button
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'perplexity-send-button';
    btn.className = 'button default'; // Django admin green style
    btn.innerText = 'Enviar a Perplexity';

    // Add margin for spacing
    btn.style.marginTop = '24px';
    btn.style.marginBottom = '18px';
    btn.style.display = 'block';

    // Insertar button despues del boton guardar y continuar editando
    continueBtn.parentNode.insertBefore(btn, continueBtn.nextSibling);

    // encontrar el articulo id
    const perplexityDiv = document.getElementById('perplexity-data');
    const articleId = perplexityDiv.dataset.articleId;

    // boton click evento
    btn.addEventListener('click', function() {
        if (articleId != '') {
        console.log('Article ID:', articleId);
        } else {
            alert('El articulo debe ser guardado antes de usar el boton de sugerencias.');
//                setPerplexityBtnStatus(btn);
            return;
        }

        const inputHeadline = document.getElementById('id_headline');
        const valorHeadline = inputHeadline ? inputHeadline.value.trim() : '';

        if (!valorHeadline) {
            alert('Por favor, escribe una pregunta para Perplexity.');
            return;
        }

        // Selecciona el textarea del cuerpo (body)
        const textareaBody = document.querySelector('textarea[id^="id_body-"]');
        const valorBody = textareaBody ? textareaBody.value.trim() : '';

        setPerplexityBtnStatus(btn, true, 'Consultando...');

        fetch('/admin/perplexity-ask/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ titulo: valorHeadline, cuerpo: valorBody, article_id: articleId})
        })
        .then(response => {
            if (!response.ok) {
                // If response is not ok (status 4xx or 5xx), throw error to catch
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error(data.message);
                alert(data.message);
                setPerplexityBtnStatus(btn);
            } else {
                  //mostrar sugerencias aqui
                  output = formatPerplexityResponse(data.message);
                  alert(output);
                  setPerplexityBtnStatus(btn);
            }
        })
        .catch((err) => {
            const msg = "Ha ocurrido un error al comunicarse con la API. Por favor, inténtalo de nuevo más tarde.";
            alert(msg);
            setPerplexityBtnStatus(btn);
            console.error(err);
        });
    });
});
