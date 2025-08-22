function resizeSubnav(container, primary, more) {
  container.classList.add('js');

  // more === 1 white transparent
  // more === 2 gray
  const svg = more === 1  ? `
    <li class="more">
      <button type="button" aria-haspopup="true" aria-expanded="false" aria-label="Mostrar todas las categorías">
        <svg xmlns="http://www.w3.org/2000/svg" width="38" height="20" viewBox="0 0 38 20"><rect width="38" height="20" rx="10" fill="#fff" opacity="0.5"/><g transform="translate(-674.803 -4175.101)"><circle cx="2" cy="2" r="2" transform="translate(699.803 4183.101)" fill="#262626"/><circle cx="2" cy="2" r="2" transform="translate(691.803 4183.101)" fill="#262626"/><circle cx="2" cy="2" r="2" transform="translate(683.803 4183.101)" fill="#262626"/></g></svg>
      </button>
    </li>` : `
    <li class="more">
      <button type="button" aria-haspopup="true" aria-expanded="false" aria-label="Mostrar todas las categorías">
        <svg xmlns="http://www.w3.org/2000/svg" width="38" height="20" viewBox="0 0 38 20"><g transform="translate(-17097 639)"><rect width="38" height="20" rx="10" transform="translate(17097 -639)" fill="#eee"/><g transform="translate(16422.197 -4814.101)"><circle cx="2" cy="2" r="2" transform="translate(699.803 4183.101)" fill="#262626"/><circle cx="2" cy="2" r="2" transform="translate(691.803 4183.101)" fill="#262626"/><circle cx="2" cy="2" r="2" transform="translate(683.803 4183.101)" fill="#262626"/></g></g></svg>
      </button>
    </li>
  `;

  primary.insertAdjacentHTML("beforeend", svg);

  container.insertAdjacentHTML("beforeend", `<ul class="secondary"></ul>`);

  const primaryItems = Array.from(primary.querySelectorAll(":scope > li:not(.more)"));
  const allItems = Array.from(primary.querySelectorAll("li"));
  const moreLi = primary.querySelector(".more");
  const moreBtn = moreLi.querySelector("button");
  const secondaryContainer = container.querySelector(".secondary");

  let isExpanded = false;

  function openMenu() {
    container.classList.add("show-secondary");
    moreBtn.setAttribute("aria-expanded", "true");
    moreLi.classList.add("hidden");
    isExpanded = true;
  }

  function closeMenu() {
    container.classList.remove("show-secondary");
    moreBtn.setAttribute("aria-expanded", "false");
    moreLi.classList.remove("hidden");
    isExpanded = false;
  }


  moreBtn.addEventListener("click", (e) => {
    e.preventDefault();
    isExpanded ? closeMenu() : openMenu();
  });

  window.addEventListener("scroll", () => {
    if (isExpanded && document.activeElement !== moreBtn) {
      closeMenu();
    }
  });

  allItems.forEach(item => {
    item.classList.remove("hidden");
  });

  const secondaryItems = [];
  let stopWidth = moreBtn.offsetWidth;
  const primaryWidth = container.offsetWidth;

  primaryItems.forEach(item => {
    const itemWidth = item.offsetWidth;
    if (primaryWidth >= stopWidth + itemWidth) {
      stopWidth += itemWidth;
    } else {
      secondaryItems.push(item);
      item.classList.add("hidden");
    }
  });

  if (secondaryItems.length === 0) {
    moreLi.classList.add("hidden");
    container.classList.remove("show-secondary");
    moreBtn.setAttribute("aria-expanded", "false");
  } else {
    primary.classList.add("full");
  }

  secondaryItems.forEach(item => {
    item.classList.remove("hidden");
    secondaryContainer.appendChild(item);
  });
}
