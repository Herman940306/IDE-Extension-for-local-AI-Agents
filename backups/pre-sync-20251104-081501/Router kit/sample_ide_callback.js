// sample_ide_callback.js
const express = require('express');
const app = express();
app.use(express.json());
app.post('/notify', (req, res) => {
  console.log('AuralA notification:', req.body);
  // Here you could display a UI toast in your extension host
  res.sendStatus(200);
});
app.listen(3000, ()=>console.log('IDE callback listening on 3000'));
