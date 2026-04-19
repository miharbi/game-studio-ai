import {EditorView, basicSetup} from 'https://esm.sh/codemirror@6';
import {markdown} from 'https://esm.sh/@codemirror/lang-markdown@6';
import {yaml} from 'https://esm.sh/@codemirror/lang-yaml@6';
import {oneDark} from 'https://esm.sh/@codemirror/theme-one-dark@6';
import {EditorState} from 'https://esm.sh/@codemirror/state@6';

export function initEditor(element, lang, content, onChange) {
  const langExt = lang === 'markdown' ? markdown() : yaml();
  const view = new EditorView({
    state: EditorState.create({
      doc: content,
      extensions: [
        basicSetup,
        langExt,
        oneDark,
        EditorView.lineWrapping,
        EditorView.updateListener.of(update => {
          if (update.docChanged && onChange) onChange(update.state.doc.toString());
        }),
      ],
    }),
    parent: element,
  });
  return view;
}

export function getContent(view) {
  return view.state.doc.toString();
}

export function setContent(view, content) {
  view.dispatch({
    changes: {from: 0, to: view.state.doc.length, insert: content},
  });
}
