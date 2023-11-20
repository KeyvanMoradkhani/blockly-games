# Task Documentation

## Overview
In this task, I made changes to the project codes to include an HTML element, add styles to a CSS file, and integrate JavaScript functionality.

## Changes Made

### html.js File
Added the following HTML code to the html.js file:

```html
<td style="width: 190px; text-align: center; vertical-align: top;">
  <svg
      id="slider"
      xmlns="http://www.w3.org/2000/svg"
      xmlns:svg="http://www.w3.org/2000/svg"
      xmlns:xlink="http://www.w3.org/1999/xlink"
      version="1.1"
      width=150
      height=50>
    <!-- Slow icon. -->
    <clipPath id="slowClipPath">
      <rect width=26 height=12 x=5 y=14 />
    </clipPath>
    <image xlink:href="common/icons.png" height=63 width=84 x=-21 y=-10
        clip-path="url(#slowClipPath)" />
    <!-- Fast icon. -->
    <clipPath id="fastClipPath">
      <rect width=26 height=16 x=120 y=10 />
    </clipPath>
    <image xlink:href="common/icons.png" height=63 width=84 x=120 y=-11
        clip-path="url(#fastClipPath)" />
  </svg>
</td>

<td style="width: 15px;">
  <img id="spinner" style="visibility: hidden;" src="common/loading.gif" loading="lazy" height=15 width=15>
</td>
```


### style.css File
Added the following Style code to the style.css file:


```css
<!-- Slider. -->
<style>
.sliderTrack {
  stroke: #aaa;
  stroke-width: 6px;
  stroke-linecap: round;
}
.sliderKnob {
  fill: #ddd;
  stroke: #bbc;
  stroke-width: 1px;
  stroke-linejoin: round;
}
.sliderKnob:hover {
  fill: #eee;
}
</style>

```

### main.js File
Added the following Js code to the main.js file:

```javascript

goog.require('Slider');

let pause = 0;
let speedSlider;

const sliderSvg = BlocklyGames.getElementById('slider');
speedSlider = new Slider(10, 35, 130, sliderSvg);

const stepSpeed = 1000 * Math.pow(1 - speedSlider.getValue(), 2);
pause = Math.max(1, stepSpeed)


```