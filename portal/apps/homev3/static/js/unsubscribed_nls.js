$(function () {
  function handleNewsletterSwitchChange(newsletterUrl, data) {
    $.ajax({
      type: "POST",
      data: data,
      url: newsletterUrl,
      cache: false,
      success: function (html, textStatus) {
        // TODO: do something?
      },
      error: function (XMLHttpRequest, textStatus, errorThrown) {
        setTimeout(function () {}, 250);
      }
    });
  }

  function generateRandomArray(length) {
    const randomArray = [];

    let arrayLength = NUMBER_OF_ITEMS_IN_MOBILE;

    if (length < 4) {
      arrayLength = length;
    }

    while (randomArray.length < arrayLength) {
      const randomNumber = Math.floor(Math.random() * length);

      if (!randomArray.includes(randomNumber)) {
        randomArray.push(randomNumber);
      }
    }

    return randomArray;
  };

  function hideCard(item, incomingItem) {
    let width = item.offsetWidth;
    let currentIndex = item.dataset.currentIndex;

    item.style.opacity = 0;
    item.style.zIndex = 0;

    if (!incomingItem.classList.contains('is-placeholder')) incomingItem.style.position = "absolute";

    incomingItem.style.left = `${positions[currentIndex]}px`;
    incomingItem.style.display = "flex";
    incomingItem.style.width = `${width}px`;
    incomingItem.dataset.currentIndex = currentIndex;
    incomingItem.style.zIndex = Number(currentIndex) + 1;

    delete item.dataset.currentIndex;
  }

  function showCard(item, incomingItem) {
    item.style.left = '';
    item.style.opacity = 0;
    item.classList.remove("displayed");
    incomingItem.style.opacity = 1;
    incomingItem.classList.add("displayed");
  }

  function moveItemToTheirIndexPositionMinusOne(item) {
    const currentPosition = Number(item.dataset.currentIndex);
    const newPosition = currentPosition - 1;

    item.style.transition = "all 0.5s ease-in-out";
    item.style.width = `${item.offsetWidth}px`;
    item.dataset.currentIndex = newPosition;

    setTimeout(() => {
      item.style.position = "absolute";
      item.style.left = `${positions[newPosition]}px`;
    }, 500);
  }

  function switchElementsAndIndexes(item, incomingItem) {
    const itemClone = item.cloneNode(true);
    const incomingItemClone = incomingItem.cloneNode(true);

    const list = document.getElementById("main-unsubscribed-list");

    const itemId = item.id;
    const incomingItemId = incomingItem.id;

    list.replaceChild(itemClone, incomingItem);
    list.replaceChild(incomingItemClone, item);

    const newItem = document.getElementById(itemId);
    const newIncomingItem = document.getElementById(incomingItemId);

    // Switch data-initial-index and current-index
    const tempIntialIndex = newIncomingItem.dataset.initialIndex;
    newIncomingItem.dataset.initialIndex = newItem.dataset.initialIndex;
    newIncomingItem.dataset.currentIndex = newItem.dataset.initialIndex;
    newItem.dataset.initialIndex = tempIntialIndex;

    // Because elements are switched in the DOM, we need to create a hack to execute the change of
    // the opacity of the incoming element at the end of the thread
    // TODO: This is a hack because of render timing
    setTimeout(() => {
      newIncomingItem.style.opacity = 0;
      incomingItemClone.style.transition = "opacity 0.5s ease-in-out";
      newIncomingItem.style.opacity = 1;
      newIncomingItem.style.zIndex = Number(newIncomingItem.dataset.currentIndex) + 1;
      newIncomingItem.classList.add("displayed");
    }, 10);

    newItem.style.opacity = 0;
    newItem.classList.remove("displayed");
    newItem.style.zIndex = 0;

    handleSwitchInputChange(newIncomingItem);

    return [newItem, newIncomingItem];
  }

  function toggleAndswitchNLElements(item, incomingItem, event) {
    item.style.opacity = 0;

    setTimeout(() => {
      const [newItem] = switchElementsAndIndexes(item, incomingItem);

      delete newItem.dataset.currentIndex;
    }, 500);
  }

  function reloadCards(event) {
    event.target.disabled = true;

    const itemsDisplayed = document.querySelectorAll(".displayed");
    if (itemsDisplayed.length < NUMBER_OF_ITEMS_IN_MOBILE) return;

    const itemsInThePoll = document.querySelectorAll(".available-to-pull:not(.displayed)");
    const randomNumbersArray = generateRandomArray(itemsInThePoll.length);

    let atLeastOneElementChange = false;

    for (let i = 0; i < itemsDisplayed.length; i++) {
      let item = itemsDisplayed[i];
      let incomingItem = itemsInThePoll[randomNumbersArray[i]];

      // No incoming items
      if (!incomingItem) {
        item.style.opacity = 0;

        setTimeout(() => {
          item.style.opacity = 1;
        }, 500);
        continue;
      };

      // Incoming item is in absolute possition
      if (!incomingItem.classList.contains("is-placeholder")) {
        hideCard(item, incomingItem);

        setTimeout(() => {
          showCard(item, incomingItem);
        }, 500);

        // Both items are placeholder
      } else if (item.classList.contains("is-placeholder") && incomingItem.classList.contains("is-placeholder")) {
        toggleAndswitchNLElements(item, incomingItem);

        // Incoming item is placeholder
      } else if (incomingItem.classList.contains("is-placeholder")) {
        item.style.opacity = 0;
        incomingItem.style.opacity = 0;

        let elementToSwitch = document.querySelector(`[data-initial-index="${item.dataset.currentIndex}"]`);

        if (incomingItem.id === elementToSwitch.id) {
          incomingItem.dataset.currentIndex = item.dataset.currentIndex;

          item.classList.remove("displayed");
          delete item.dataset.currentIndex;

          setTimeout(() => {
            incomingItem.classList.add("displayed");
            incomingItem.style.opacity = 1;
          }, 500);
          continue;
        }

        elementToSwitch.style.opacity = 0;

        setTimeout(() => {
          if (atLeastOneElementChange) {
            const updatedItem = document.getElementById(item.id);
            elementToSwitch = document.querySelector(`[data-initial-index="${updatedItem.dataset.currentIndex}"]`);
            incomingItem = document.getElementById(incomingItem.id);
          }

          switchElementsAndIndexes(elementToSwitch, incomingItem);

          item.style.opacity = 0;
          item.classList.remove("displayed");
          item.style.zIndex = 0;
          delete item.dataset.currentIndex;
        }, 500);


        atLeastOneElementChange = true;
        continue;
      }
    }
    setTimeout(() => {
      event.target.disabled = false;
    }, 750);
  }

  function handleSwitchInputChange(item) {
    const itemInput = item.querySelector('input[type="checkbox"]');
    const dataKey = itemInput.getAttribute('data-key');
    const offLabel = item.querySelector('.off');
    const onLabel = item.querySelector('.on');
    if (offLabel) offLabel.style.display = itemInput.checked ? "none" : "inline-block";
    if (onLabel) onLabel.style.display = itemInput.checked ? "inline-block" : "none";

    itemInput.addEventListener("change", (e) => {
      if (initialTimeOutId[item.id]) {
        clearTimeout(initialTimeOutId[item.id]);
        return;
      }
      if (finalTimeOutId[item.id]) {
        clearTimeout(finalTimeOutId[item.id]);
      }
      nlItemsList.scrollLeft = scrollPosition;

      const slider = item.querySelector(".slider");
      const newsletterUrl = itemInput.getAttribute('data-url');
      slider.style.backgroundColor = itemInput.checked ? "#6FCF97" : "#ccc";
      offLabel.style.display = itemInput.checked ? "none" : "inline-block";
      onLabel.style.display = itemInput.checked ? "inline-block" : "none";
      item.classList.toggle("selected");

      handleNewsletterSwitchChange(newsletterUrl, { [dataKey]: itemInput.checked });
      item.classList.remove("available-to-pull");

      const availableItems = document.querySelectorAll(".available-to-pull:not(.displayed)");
      if (availableItems.length === 0) {
        const updatedItems = document.querySelectorAll(".choose-nl-item.displayed");
        for (let updatedItem of updatedItems) {
          if (updatedItem.dataset.currentIndex > item.dataset.currentIndex) {
            moveItemToTheirIndexPositionMinusOne(updatedItem);
          } else {
            item.style.opacity = 0;
            item.classList.remove("displayed");
            if (updatedItems.length === 1) {
              setTimeout(() => {
                const message = document.getElementById("all-nl-marked-message");
                message.style.display = "flex";
                message.style.opacity = 1;
              }, 500);
            }
          }
        }
        const seeMoreNLBtnMobile = document.getElementById("see-more-nl-mobile");
        document.getElementById("see-more-nl-desktop").disabled = true;
        if (updatedItems.length === 1) {
          seeMoreNLBtnMobile.style.display = "none";
        } else {
          seeMoreNLBtnMobile.disabled = true;
          setTimeout(() => {// move see more
            const newLeftPosition = Number(seeMoreNLBtnMobile.style.left.replace("px", "")) - item.offsetWidth;
            seeMoreNLBtnMobile.style.left = `${newLeftPosition}px`;
          }, 500);
        }
        return;
      }

      const randomNumber = Math.floor(Math.random() * availableItems.length)
      let incomingItem = availableItems[randomNumber];

      if (incomingItem.classList.contains("is-placeholder") && item.classList.contains("is-placeholder")) {
        toggleAndswitchNLElements(item, incomingItem);
        return;
      } else if (incomingItem.classList.contains("is-placeholder")) { // TODO: REfactor this part
        let elementToSwitch = document.querySelector(`[data-initial-index="${item.dataset.currentIndex}"]`);

        if (incomingItem.id === elementToSwitch.id) {
          incomingItem.style.opacity = 0;
          incomingItem.dataset.currentIndex = item.dataset.currentIndex;

          item.style.opacity = 0;
          item.classList.remove("displayed");
          delete item.dataset.currentIndex;

          setTimeout(() => {
            incomingItem.classList.add("displayed");
            incomingItem.style.opacity = 1;
          }, 500);
          return;
        }

        incomingItem.style.opacity = 0;
        elementToSwitch.style.opacity = 0;
        item.style.opacity = 0;

        setTimeout(() => {
          switchElementsAndIndexes(elementToSwitch, incomingItem);

          item.style.opacity = 0;
          item.classList.remove("displayed");
          item.style.zIndex = 0;
          delete item.dataset.currentIndex;
        }, 500);
        return;
      }

      // TODO: need to clean timeout
      initialTimeOutId[item.id] = setTimeout(() => {
        hideCard(item, incomingItem);
      }, 1000);

      finalTimeOutId[item.id] = setTimeout(() => {
        showCard(item, incomingItem);
      }, 1500);
    });
  }

  let scrollPosition;
  const NUMBER_OF_ITEMS_IN_MOBILE = 4;
  let initialTimeOutId = {};
  let finalTimeOutId = {};
  const positions = {};

  const nlItemsList = document.querySelector(".choose-nl-body");
  nlItemsList.addEventListener("scroll", (e) => {
    scrollPosition = e.target.scrollLeft;
  });
  const listContainer = document.querySelector(".choose-nl-list");
  listContainer.style.height = `${listContainer.offsetHeight}px`;

  // Get both desktop and mobile See More buttons
  const seeMoreBtns = document.getElementsByClassName("see-more-nls-btn");
  for (let seeMoreBtn of seeMoreBtns) {
    if (seeMoreBtn.id === "see-more-nl-mobile") {
      const leftPosition = `${seeMoreBtn.offsetLeft}`;
      seeMoreBtn.style.position = "absolute";
      seeMoreBtn.style.left = `${leftPosition}px`;
    }
    seeMoreBtn.addEventListener("click", (e) => {
      if (e.target.id === "see-more-nl-mobile") {
        nlItemsList.scrollLeft = 0;
      }
      reloadCards(e);
    });
  }

  const items = document.querySelectorAll(".choose-nl-item");
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (i < NUMBER_OF_ITEMS_IN_MOBILE) {
      positions[i] = item.offsetLeft;
    }
    handleSwitchInputChange(item);
  }

  $("#choose-nl-dismiss-btn").on("click", function(){
    $("#choose-nl-container").hide();
    $.post($(this).data("url"));
  });
});
