/** Proíbe comentários, exceto JSDoc. Diretivas de ferramenta também contam como comentário. */
const noComments = {
  meta: {
    type: "suggestion",
    docs: { description: "Proíbe comentários de linha e de bloco; JSDoc é permitido" },
    schema: [],
    messages: { forbidden: "Comentário proibido: deixe o código se explicar (JSDoc é permitido)." },
  },
  create(context) {
    return {
      Program() {
        for (const comment of context.sourceCode.getAllComments()) {
          const isJsDoc = comment.type === "Block" && comment.value.startsWith("*");
          if (!isJsDoc) context.report({ loc: comment.loc, messageId: "forbidden" });
        }
      },
    };
  },
};

/** Proíbe if dentro de if, sem contar funções internas (callbacks, componentes). */
const noNestedIf = {
  meta: {
    type: "suggestion",
    docs: { description: "Proíbe if dentro de if" },
    schema: [],
    messages: { nested: "if dentro de if: extraia uma função ou combine as condições." },
  },
  create(context) {
    const depth = [0];
    const enterScope = () => depth.push(0);
    const exitScope = () => depth.pop();
    return {
      FunctionDeclaration: enterScope,
      "FunctionDeclaration:exit": exitScope,
      FunctionExpression: enterScope,
      "FunctionExpression:exit": exitScope,
      ArrowFunctionExpression: enterScope,
      "ArrowFunctionExpression:exit": exitScope,
      IfStatement(node) {
        if (depth[depth.length - 1] > 0) context.report({ node, messageId: "nested" });
        depth[depth.length - 1] += 1;
      },
      "IfStatement:exit"() {
        depth[depth.length - 1] -= 1;
      },
    };
  },
};

const plugin = { rules: { "no-comments": noComments, "no-nested-if": noNestedIf } };

export default plugin;
