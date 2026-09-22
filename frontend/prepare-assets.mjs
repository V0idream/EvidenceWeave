import {cpSync,mkdirSync} from 'node:fs';
for(const folder of ['cmaps','standard_fonts','wasm']){
  mkdirSync('public/pdfjs/'+folder,{recursive:true});
  cpSync('node_modules/pdfjs-dist/'+folder,'public/pdfjs/'+folder,{recursive:true});
}
