# Ditwo: Differential Testing framework for Wasm Optimizers

<p align="center">
  <img src="https://github.com/monkbai/wasm-testing/blob/main/doc/ditwo.png?raw=true" width="120" title="ditwo-logo">
</p>
<br />

Artifact for our draft "Exploring Missed Optimizations in WebAssembly Optimizers".

We aim to present the first systematic and in-depth understanding 
of the status quo of wasm optimizations with **Ditwo**, a 
**Di**fferential **T**esting framework to uncover missed optimizations (MO) 
of **W**asm **O**ptimizers. Ditwo compiles a C program into both native x86 
executable and wasm executable, and differentiates *optimization indication traces* 
(OITraces) logged by running each executable to uncover MO. Each OITrace 
is composed with global variable writes and function calls, two performance
indicators that practically and systematically reflect the optimization 
degree across wasm and native executables.

<p align="center">
  <img src="https://github.com/monkbai/wasm-testing/blob/main/workflow.png?raw=true" width="881" title="ditwo-workflow">
</p>
<br />
