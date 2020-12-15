// IIFE - Immediately Invoked Function Expression
(function(markdown_help) {

    // The global jQuery object is passed as a parameter
    markdown_help(window.jQuery, window, document);

}(function($, window, document) {

    // The $ is now locally scoped 

    // Listen for the jQuery ready event on the document
    $(function() {


        // The DOM is ready!
        var body = $('div.field-body');
        var help = "<div class='markdown-help'>\n \
    <a href='#' class='toggle-markdown-help'>Sintaxis Markdown</a>\n \
    <pre class='syntax'>\n \
# Cabezales \n \
\n \
De forma simple:\n \
\n \
# Título H1\n \
## Título H2\n \
### Título H3\n \
\n \
otro h1\n \
==========\n \
\n \
otro h2\n \
----------\n \
\n \
# Estilos\n \
\n \
Se puede usar tanto asteríscos (*)\n \ cómo subguiones (_).\n \
\n \
**Esto es todo negrita**\n \
\n \
_Esto es una italica_\n \
\n \
***Esto es todo negrita con italica***\n \ porque tiene 3 asteriscos (o subguiones)\n \
\n \
Y **esto negrita y _esto negrita\n \ con italica_**\n \
\n \
Y _esto_ es italica también.\n \
\n \
Si se quiere dejar algo modificado pero\n \ tachado se puede envolver en la etiqueta `<del></del>` \n \ y <del>tachar el texto viejo</del>.\n \
\n \
# Listas\n \
\n \
## Sin orden\n \
\n \
Junta:\n \
\n \
* asterisk 1\n \
* asterisk 2\n \
* asterisk 3\n \
\n \
\n \
Suelta:\n \
\n \
* asterisk 1\n \
\n \
* asterisk 2\n \
\n \
* asterisk 3\n \
\n \
## Ordenadas\n \
\n \
Apretado:\n \
\n \
1. First\n \
2. Second\n \
3. Third\n \
\n \
\n \
Suelto:\n \
\n \
1. First\n \
\n \
2. Second\n \
\n \
3. Third\n \
\n \
Parrafo dentro de lista:\n \
\n \
1. Item 1, graf one.\n \
\n \
 Item 2. graf two. The quick brown fox\n \ jumped over the lazy dog's\n \
 back.\n \
 \n \
2. Item 2.\n \
\n \
3. Item 3.\n \
\n \
\n \
## Lista dentro de lista\n \
\n \
* Tab\n \
 * Tab\n \
  * Tab\n \
\n \
Mezclado ordenada y sin orden\n \
\n \
1. First\n \
2. Second:\n \
 * Fee\n \
 * Fie\n \
 * Foe\n \
3. Third\n \
\n \
# Links\n \
\n \
Aquí hay un [link](/url/ 'con título')\n \ y otro [link](/url/) sin título.\n \
\n \
[1]: http://ladiaria.com.uy \n \'La Diaria'\n \
\n \
\n \
También podemos linkear referenciado\n \ con nombres a [la diaria][] por ejemplo.\n \
\n \
[la diaria]: http://ladiaria.com.uy 'El diario que depende solo de vos'\n \
\n \
## Notas al pie\n \
\n \
Este es un parrafo que tiene una nota al pié. [^note-id]\n \
\n \
[^note-id]: Esta es la nota al pié, que siempre\n \ la pone al final del cuerpo del artículo. \n \
\n \
\n \
# Blocks\n \
\n \
> foo\n \
>\n \
> > bar\n \
>\n \
> foo\n \
\n \
\n \
> ## Una lista en un bloque con cabezal\n \
> * asterisk 1\n \
> * asterisk 2\n \
> * asterisk 3\n \
\n \
# Dashes:\n \
\n \
---\n \
\n \
# Tablas\n \
\n \
|| *año* || *temp (min)* || *temp (max)* ||\n \
|| 1900 || -10 || 25 ||\n \
|| 1910 || -15 || 30 ||\n \
|| *1920* || -10 || *32* ||\n \
    </pre></div>";

        body.find('textarea').after(help);

        var link = body.find('a.toggle-markdown-help')
        var syntax = body.find('pre.syntax')
        syntax.toggle();

        link.click(function(event) {
            event.preventDefault()
            syntax.toggle();
        });

    });


    // The rest of code goes here!

}));
