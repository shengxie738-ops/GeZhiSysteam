const { compile } = require('@vue/compiler-dom');
try {
    compile("<div v-if='a'></div><teleport v-else-if='b' to='body'></teleport><div v-else-if='c'></div>");
    console.log('success');
} catch(e) {
    console.error('Error:', e.message);
}
