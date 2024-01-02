// taken from martor.semantic.js to also allow "h4" (only for the "body" field)

// win/linux: Ctrl+Alt+4, mac: Command+Option+4
var markdownToH4 = function(editor) {
    var originalRange = editor.getSelectionRange();
    if (editor.selection.isEmpty()) {
        var curpos = editor.getCursorPosition();
        editor.session.insert(curpos, '\n\n#### ');
        editor.focus();
        editor.selection.moveTo(curpos.row+2, curpos.column+5);
    }
    else {
        var range = editor.getSelectionRange();
        var text = editor.session.getTextRange(range);
        editor.session.replace(range, '\n\n#### '+text+'\n');
        editor.focus();
        editor.selection.moveTo(
            originalRange.end.row+2,
            originalRange.end.column+5
        );
    }
};
if (window.jQuery) {
    $(function(){
        if (typeof ace !== "undefined") {
            var editor = ace.edit('martor-body');
            editor.commands.addCommand({
                name: 'markdownToH4',
                bindKey: {win: 'Ctrl-Alt-4', mac: 'Command-Option-4'},
                exec: function(editor) {
                    markdownToH4(editor);
                },
                readOnly: true
            });
        }
    });
}
