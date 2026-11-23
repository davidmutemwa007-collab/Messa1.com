/* Original layered SVG food illustrations. The layers are animated by app.css. */
(() => {
  let artSequence = 0;
  const uniqueIds = svg => {
    const suffix = `-${++artSequence}`;
    return svg.replace(/\bid="([^"]+)"/g, (_match, id) => `id="${id}${suffix}"`)
      .replace(/url\(#([^)]+)\)/g, (_match, id) => `url(#${id}${suffix})`);
  };

  const burger = (vegetarian = false) => `
  <svg class="food-art ${vegetarian ? 'burger-veg-art' : 'burger-art'}" viewBox="0 0 520 470" role="img" aria-label="Illustrated ${vegetarian ? 'garden' : 'smash'} burger with animated separated ingredients">
    <defs>
      <linearGradient id="bunGold" x1="0" y1="0" x2=".15" y2="1"><stop stop-color="#ffd98b"/><stop offset="1" stop-color="#d97934"/></linearGradient>
      <linearGradient id="bunLight" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#ffe3a5"/><stop offset="1" stop-color="#e89a4d"/></linearGradient>
      <linearGradient id="patty" x1="0" y1="0" x2=".2" y2="1"><stop stop-color="#75402d"/><stop offset="1" stop-color="#3d241e"/></linearGradient>
      <linearGradient id="cheese" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffe878"/><stop offset="1" stop-color="#f2a82c"/></linearGradient>
      <filter id="foodShadow" x="-30%" y="-30%" width="160%" height="180%"><feGaussianBlur stdDeviation="11"/></filter>
    </defs>
    <ellipse cx="262" cy="403" rx="175" ry="21" fill="#28251e" opacity=".13" filter="url(#foodShadow)"/>
    <g class="ingredient bun-bottom"><path d="M100 337 Q111 319 145 319 H379 Q414 322 424 344 L412 368 Q405 382 385 382 H137 Q114 381 106 363Z" fill="url(#bunLight)" stroke="#bd6c36" stroke-width="5"/><path d="M126 352 Q260 372 398 351" fill="none" stroke="#fff0c9" stroke-width="6" stroke-linecap="round" opacity=".55"/></g>
    <g class="ingredient burger-patty"><path d="M95 305 Q104 281 141 278 L378 279 Q414 281 428 305 L417 326 Q408 338 387 338 H131 Q109 337 101 324Z" fill="url(#patty)" stroke="#40251d" stroke-width="5"/><path d="M126 300 Q235 282 390 300" fill="none" stroke="#a96c43" stroke-width="5" opacity=".7"/><path d="M170 320 l23 -6 M281 321 l25 -8 M350 311 l18 2" stroke="#d28b55" stroke-width="4" stroke-linecap="round"/></g>
    <g class="ingredient cheese-layer"><path d="M108 274 L403 270 L424 316 L370 304 L326 326 L264 304 L207 327 L168 305 L112 318Z" fill="url(#cheese)" stroke="#df941e" stroke-width="4"/><path d="M127 281 L382 279" stroke="#fff5a9" stroke-width="5" opacity=".75" stroke-linecap="round"/></g>
    <g class="ingredient tomato-layer"><path d="M112 257 Q128 231 164 235 H361 Q396 233 414 257 L402 273 H125Z" fill="#e9513c" stroke="#b7352b" stroke-width="4"/><path d="M143 248 Q254 235 385 249" fill="none" stroke="#ff9b76" stroke-width="5" stroke-linecap="round"/></g>
    <g class="ingredient lettuce-layer"><path d="M104 237 Q120 211 140 222 Q151 201 171 220 Q194 196 215 217 Q232 199 252 218 Q275 195 298 217 Q323 198 341 220 Q367 199 386 222 Q412 207 424 237 L411 252 Q390 243 374 253 Q350 241 333 253 Q309 241 290 254 Q268 241 245 254 Q220 241 202 253 Q180 241 160 252 Q132 240 115 252Z" fill="#73a64c" stroke="#477e3a" stroke-width="4"/><path d="M130 235 l14 -4 M195 234 l12 -7 M320 237 l17 -8 M378 234 l13 0" stroke="#b7d77b" stroke-width="5" stroke-linecap="round"/></g>
    <g class="ingredient top-bun"><path d="M103 216 C106 141 166 91 260 89 C354 88 414 140 418 216 Q417 228 402 231 H119 Q102 229 103 216Z" fill="url(#bunGold)" stroke="#bc6b35" stroke-width="5"/><path d="M132 186 C162 130 220 115 268 115 C321 115 371 141 390 185" fill="none" stroke="#ffedbd" stroke-width="8" stroke-linecap="round" opacity=".7"/><g fill="#fff0c5"><ellipse cx="190" cy="157" rx="4" ry="8" transform="rotate(-30 190 157)"/><ellipse cx="230" cy="133" rx="4" ry="8" transform="rotate(18 230 133)"/><ellipse cx="288" cy="132" rx="4" ry="8" transform="rotate(-9 288 132)"/><ellipse cx="336" cy="158" rx="4" ry="8" transform="rotate(32 336 158)"/><ellipse cx="365" cy="185" rx="4" ry="8" transform="rotate(-16 365 185)"/></g></g>
    <g class="ingredient-label label-brioche"><path d="M399 139 L438 111 H506"/><text x="439" y="103">BRIOCHE</text></g>
    <g class="ingredient-label label-lettuce"><path d="M115 231 L76 205 H10"/><text x="11" y="196">LETTUCE</text></g>
    <g class="ingredient-label label-tomato"><path d="M405 259 L446 238 H509"/><text x="447" y="229">TOMATO</text></g>
    <g class="ingredient-label label-cheese"><path d="M116 294 L77 308 H9"/><text x="10" y="326">CHEDDAR</text></g>
    <g class="ingredient-label label-beef"><path d="M411 318 L451 342 H508"/><text x="452" y="359">BEEF PATTY</text></g>
    <g class="sparkle sparkle-one"><path d="M55 160 v28 M41 174 h28" stroke="#e66b46" stroke-width="5" stroke-linecap="round"/><circle cx="55" cy="174" r="3" fill="#e66b46"/></g>
    <g class="sparkle sparkle-two"><path d="M443 132 v22 M432 143 h22" stroke="#e66b46" stroke-width="4" stroke-linecap="round"/></g>
  </svg>`;

  const pizza = (vegetarian = false) => `
  <svg class="food-art ${vegetarian ? 'pizza-veg-art' : 'pizza-art'}" viewBox="0 0 520 470" role="img" aria-label="Illustrated stone-baked pizza with lively toppings">
    <defs>
      <radialGradient id="pizzaCheese"><stop stop-color="#fff0ae"/><stop offset=".72" stop-color="#f8d477"/><stop offset="1" stop-color="#edae4b"/></radialGradient>
      <linearGradient id="pizzaCrust" x1=".2" y1="0" x2=".8" y2="1"><stop stop-color="#ffe2a0"/><stop offset="1" stop-color="#c97a3d"/></linearGradient>
      <filter id="pizzaShadow"><feGaussianBlur stdDeviation="10"/></filter>
    </defs>
    <ellipse cx="260" cy="390" rx="178" ry="22" fill="#252219" opacity=".14" filter="url(#pizzaShadow)"/>
    <g class="pizza-body"><circle class="pizza-crust-ring" cx="260" cy="235" r="166" fill="url(#pizzaCrust)" stroke="#b96635" stroke-width="7"/><circle class="pizza-cheese-base" cx="260" cy="235" r="143" fill="url(#pizzaCheese)" stroke="#f2b84c" stroke-width="5"/><g class="pizza-cuts" fill="none" stroke="#dcae60" stroke-width="4" opacity=".62" stroke-linecap="round"><path d="M260 92 L260 235 L342 354"/><path d="M119 317 L260 235 L403 153"/><path d="M178 100 L260 235 L342 354"/></g><path d="M143 184 Q252 117 369 187 M125 251 Q249 314 392 247" stroke="#fff9dc" stroke-width="13" opacity=".42" fill="none" stroke-linecap="round"/></g>
    <g class="pizza-toppings">
      ${vegetarian ? `
      <g class="topping topping-a"><ellipse cx="194" cy="166" rx="18" ry="13" fill="#b65a40"/><ellipse cx="194" cy="166" rx="8" ry="5" fill="#e3a16a"/><path d="M180 166 q14 -20 28 0" stroke="#743d32" stroke-width="4" fill="none"/></g>
      <g class="topping topping-b"><path d="M295 146 q28 -12 35 13 q-16 27 -39 12 q-9 -12 4 -25" fill="#74a75a"/><path d="M300 151 l20 14" stroke="#d1e5a9" stroke-width="4"/></g>
      <g class="topping topping-c"><circle cx="334" cy="245" r="17" fill="#596a35"/><circle cx="334" cy="245" r="8" fill="#f8d477"/><circle cx="164" cy="267" r="15" fill="#596a35"/><circle cx="164" cy="267" r="7" fill="#f8d477"/></g>
      <g class="topping topping-d"><path d="M246 214 q-28 -26 -18 -39 q16 -12 29 12 q-2 -25 16 -28 q21 12 -2 36 q27 -12 33 4 q-5 22 -35 17 q13 24 -4 34 q-18 -2 -19 -36" fill="#4c914d" stroke="#337643" stroke-width="3"/></g>
      ` : `
      <g class="topping topping-a"><circle cx="180" cy="173" r="24" fill="#c63830" stroke="#a92d2a" stroke-width="4"/><circle cx="180" cy="173" r="12" fill="#f7795a"/><circle cx="338" cy="201" r="24" fill="#c63830" stroke="#a92d2a" stroke-width="4"/><circle cx="338" cy="201" r="12" fill="#f7795a"/></g>
      <g class="topping topping-b"><circle cx="253" cy="142" r="22" fill="#c63830" stroke="#a92d2a" stroke-width="4"/><circle cx="253" cy="142" r="10" fill="#f7795a"/><circle cx="236" cy="292" r="23" fill="#c63830" stroke="#a92d2a" stroke-width="4"/><circle cx="236" cy="292" r="11" fill="#f7795a"/></g>
      <g class="topping topping-c"><path d="M286 218 q-28 -24 -17 -40 q16 -11 29 12 q0 -26 18 -27 q20 13 -3 36 q27 -10 32 7 q-7 21 -35 15 q11 23 -7 33 q-18 -3 -17 -36" fill="#4c914d" stroke="#337643" stroke-width="3"/><path d="M141 251 q-17 -17 -6 -28 q14 -7 22 11 q4 -18 18 -16 q13 13 -7 25 q20 -4 21 10 q-9 14 -27 5 q5 18 -9 23 q-13 -4 -12 -30" fill="#4c914d" stroke="#337643" stroke-width="3"/></g>
      <g class="topping topping-d"><circle cx="286" cy="298" r="8" fill="#fff3c4"/><circle cx="204" cy="235" r="7" fill="#fff3c4"/><circle cx="353" cy="276" r="7" fill="#fff3c4"/></g>
      `}
    </g>
    <g class="pizza-herbs" fill="#4b8c48"><ellipse cx="302" cy="174" rx="5" ry="11" transform="rotate(48 302 174)"/><ellipse cx="165" cy="218" rx="5" ry="10" transform="rotate(-33 165 218)"/><ellipse cx="294" cy="260" rx="5" ry="10" transform="rotate(25 294 260)"/><ellipse cx="222" cy="195" rx="4" ry="9" transform="rotate(65 222 195)"/></g>
    <g class="ingredient-label pizza-label label-pepperoni"><path d="M180 173 L127 132 H13"/><text x="14" y="123">PEPPERONI</text></g>
    <g class="ingredient-label pizza-label label-mozzarella"><path d="M336 201 L391 166 H507"/><text x="392" y="157">MOZZARELLA</text></g>
    <g class="ingredient-label pizza-label label-basil"><path d="M292 228 L343 337 H505"/><text x="400" y="354">FRESH BASIL</text></g>
    <g class="sparkle sparkle-one"><path d="M65 155 v26 M52 168 h26" stroke="#e66b46" stroke-width="5" stroke-linecap="round"/></g><g class="sparkle sparkle-two"><path d="M441 285 v20 M431 295 h20" stroke="#e66b46" stroke-width="4" stroke-linecap="round"/></g>
  </svg>`;

  const icecream = `
  <svg class="food-art icecream-art" viewBox="0 0 520 470" role="img" aria-label="Illustrated vanilla and strawberry ice cream sundae">
    <defs><linearGradient id="cone" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e8a34c"/><stop offset="1" stop-color="#a95e31"/></linearGradient><radialGradient id="scoopVanilla"><stop stop-color="#fff5d8"/><stop offset="1" stop-color="#e7b879"/></radialGradient><radialGradient id="scoopPink"><stop stop-color="#ffc6c2"/><stop offset="1" stop-color="#e6757a"/></radialGradient><filter id="iceShadow"><feGaussianBlur stdDeviation="10"/></filter></defs>
    <ellipse cx="258" cy="405" rx="115" ry="18" fill="#29241c" opacity=".14" filter="url(#iceShadow)"/>
    <g class="cone-group"><path d="M158 250 L362 250 L272 406 Q260 422 247 405Z" fill="url(#cone)" stroke="#9f5a30" stroke-width="5"/><path d="M178 269 L328 269 M190 300 L309 300 M207 331 L292 331 M225 362 L276 362" stroke="#f7c477" stroke-width="7" opacity=".8"/><path d="M194 267 L285 380 M250 264 L317 339 M318 267 L229 380 M273 265 L198 348" stroke="#a96134" stroke-width="5" opacity=".55"/></g>
    <g class="scoop scoop-bottom"><circle cx="255" cy="248" r="83" fill="url(#scoopVanilla)" stroke="#d9a56d" stroke-width="4"/><path d="M192 255 q16 31 45 34 q31 4 49 -16" stroke="#fff8e9" stroke-width="9" fill="none" stroke-linecap="round"/></g>
    <g class="scoop scoop-top"><circle cx="252" cy="146" r="78" fill="url(#scoopPink)" stroke="#d76772" stroke-width="4"/><path d="M198 147 q14 -39 54 -43 q36 -2 51 28" stroke="#ffe7dc" stroke-width="9" fill="none" stroke-linecap="round" opacity=".8"/></g>
    <g class="cream-swirl"><path d="M211 87 Q204 54 240 48 Q273 38 286 63 Q299 85 268 92 Q244 98 250 72 Q255 58 272 62" fill="none" stroke="#fff7e7" stroke-width="17" stroke-linecap="round"/><path d="M221 86 Q236 65 256 74" fill="none" stroke="#e7c9a5" stroke-width="4" stroke-linecap="round"/></g>
    <g class="sauce-drip"><path d="M185 157 Q159 177 182 197 Q205 201 207 180 M306 167 Q329 187 313 206" stroke="#8b3e34" stroke-width="8" fill="none" stroke-linecap="round"/></g>
    <g fill="#f7e7b4" class="sprinkles"><rect x="198" y="116" width="8" height="19" rx="4" transform="rotate(-35 198 116)"/><rect x="289" y="127" width="8" height="18" rx="4" transform="rotate(42 289 127)"/><rect x="239" y="185" width="8" height="17" rx="4" transform="rotate(18 239 185)"/><rect x="274" y="204" width="8" height="15" rx="4" transform="rotate(-28 274 204)"/></g>
    <g class="sparkle sparkle-one"><path d="M85 165 v28 M71 179 h28" stroke="#e66b46" stroke-width="5" stroke-linecap="round"/></g><g class="sparkle sparkle-two"><path d="M411 130 v22 M400 141 h22" stroke="#e66b46" stroke-width="4" stroke-linecap="round"/></g>
  </svg>`;

  const drink = (shake = false) => `
  <svg class="food-art ${shake ? 'shake-art' : 'drink-art'}" viewBox="0 0 520 470" role="img" aria-label="Illustrated ${shake ? 'mango milkshake' : 'pink citrus sparkling drink'}">
    <defs><linearGradient id="glassFill" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff" stop-opacity=".8"/><stop offset=".5" stop-color="#dff4ed" stop-opacity=".42"/><stop offset="1" stop-color="#8ac9c5" stop-opacity=".65"/></linearGradient><linearGradient id="drinkLiquid" x1="0" y1="0" x2="0" y2="1"><stop stop-color="${shake ? '#ffe18b' : '#f3a0a2'}"/><stop offset="1" stop-color="${shake ? '#e9a849' : '#d95870'}"/></linearGradient><filter id="drinkShadow"><feGaussianBlur stdDeviation="10"/></filter></defs>
    <ellipse cx="258" cy="403" rx="99" ry="17" fill="#25231e" opacity=".12" filter="url(#drinkShadow)"/>
    <g class="glass-group"><path d="M172 110 H348 L326 365 Q323 386 305 386 H215 Q197 386 194 365Z" fill="url(#glassFill)" stroke="#a5c7be" stroke-width="6"/><path d="M184 195 H336 L321 361 Q319 372 305 372 H215 Q203 372 201 359Z" fill="url(#drinkLiquid)" opacity=".9"/><path d="M187 194 Q256 211 334 194" fill="none" stroke="#fff4da" stroke-width="7" opacity=".85"/><path d="M205 225 L221 354" stroke="#fff" stroke-width="10" opacity=".45" stroke-linecap="round"/><path d="M318 231 L308 325" stroke="#fff" stroke-width="5" opacity=".35" stroke-linecap="round"/></g>
    ${shake ? `<g class="whipped-cream"><path d="M177 119 Q165 89 197 85 Q196 51 233 61 Q247 29 275 56 Q305 42 312 75 Q352 71 344 109 Q331 128 300 116 Q273 139 247 117 Q210 137 177 119Z" fill="#fff6e7" stroke="#e9d9c6" stroke-width="5"/><path d="M221 84 Q244 53 265 81 Q279 55 298 83" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round"/><path d="M260 60 L270 20" stroke="#e6a34d" stroke-width="5" stroke-linecap="round"/></g>` : `<g class="citrus"><circle cx="176" cy="128" r="39" fill="#ffd56a" stroke="#e7a840" stroke-width="5"/><circle cx="176" cy="128" r="28" fill="#fff2b0"/><path d="M176 101 v54 M149 128 h54 M157 109 l38 38 M195 109 l-38 38" stroke="#f7c44f" stroke-width="4"/><path d="M303 112 q48 -59 73 -18 q-23 45 -73 18" fill="#7cab58" stroke="#548d47" stroke-width="4"/></g>`}
    <g class="straw"><path d="M283 118 L327 26" stroke="#e75d60" stroke-width="12" stroke-linecap="round"/><path d="M288 107 L326 28" stroke="#ffd9c7" stroke-width="3" stroke-linecap="round"/></g>
    <g class="bubbles" fill="#fff" opacity=".8"><circle cx="230" cy="272" r="6"/><circle cx="286" cy="310" r="5"/><circle cx="248" cy="340" r="4"/><circle cx="302" cy="250" r="7"/></g>
    <g class="sparkle sparkle-one"><path d="M91 192 v26 M78 205 h26" stroke="#e66b46" stroke-width="5" stroke-linecap="round"/></g><g class="sparkle sparkle-two"><path d="M418 164 v22 M407 175 h22" stroke="#e66b46" stroke-width="4" stroke-linecap="round"/></g>
  </svg>`;

  const fries = `
  <svg class="food-art fries-art" viewBox="0 0 520 470" role="img" aria-label="Illustrated golden parmesan fries">
    <defs><linearGradient id="friesCup" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#f06a49"/><stop offset="1" stop-color="#a94031"/></linearGradient><linearGradient id="fryGold" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffe7a2"/><stop offset="1" stop-color="#e6a33a"/></linearGradient></defs>
    <ellipse cx="260" cy="401" rx="120" ry="19" fill="#28251e" opacity=".13"/><g class="fries-sticks"><rect x="160" y="112" width="40" height="208" rx="13" fill="url(#fryGold)" stroke="#c98a32" stroke-width="4" transform="rotate(-13 180 215)"/><rect x="211" y="76" width="42" height="245" rx="13" fill="url(#fryGold)" stroke="#c98a32" stroke-width="4" transform="rotate(-4 232 198)"/><rect x="263" y="88" width="42" height="230" rx="13" fill="url(#fryGold)" stroke="#c98a32" stroke-width="4" transform="rotate(5 284 203)"/><rect x="316" y="119" width="40" height="198" rx="13" fill="url(#fryGold)" stroke="#c98a32" stroke-width="4" transform="rotate(14 336 218)"/></g><g class="fries-cup"><path d="M139 251 H381 L343 382 Q340 393 324 393 H195 Q179 393 176 381Z" fill="url(#friesCup)" stroke="#93392f" stroke-width="5"/><path d="M164 278 Q260 295 355 278" fill="none" stroke="#ffab7a" stroke-width="6" opacity=".7"/></g><g fill="#fff0c2" opacity=".85"><circle cx="195" cy="236" r="5"/><circle cx="237" cy="199" r="5"/><circle cx="290" cy="227" r="5"/><circle cx="327" cy="197" r="5"/></g><g class="sparkle sparkle-one"><path d="M78 170 v24 M66 182 h24" stroke="#e66b46" stroke-width="5" stroke-linecap="round"/></g>
  </svg>`;

  window.MesaFoodArt = {
    burger: () => uniqueIds(burger(false)), burgerVeg: () => uniqueIds(burger(true)),
    pizza: () => uniqueIds(pizza(false)), pizzaVeg: () => uniqueIds(pizza(true)),
    icecream: () => uniqueIds(icecream), drink: () => uniqueIds(drink(false)), shake: () => uniqueIds(drink(true)), fries: () => uniqueIds(fries),
  };
})();
