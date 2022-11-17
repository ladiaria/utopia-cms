const toastOptions = {
	duration: 4000,
	gravity: 'bottom',
	position: 'right',
	stopOnFocus: true,
};

const style = {
	borderRadius: '5px',
	color: '#ffffff',
	fontWeight: 'bold',
};

Toastify.error = function (text, options = {}) {
	const toast = Toastify({
		...toastOptions,
		text,
		style: { ...style, background: '#ff5252' },
		...options,
	});

	toast.showToast();

	return toast;
};

Toastify.success = function (text, options = {}) {
	const toast = Toastify({
		...toastOptions,
		text,
		style: { ...style, background: '#4caf50' },
		...options,
	});

	toast.showToast();

	return toast;
};

Toastify.warning = function (text, options = {}) {
	const toast = Toastify({
		...toastOptions,
		text,
		style: { ...style, background: '#ffc107' },
		...options,
	});

	toast.showToast();

	return toast;
};

Toastify.info = function (text, options = {}) {
	const toast = Toastify({
		...toastOptions,
		text,
		style: { ...style, background: '#2196f3' },
		...options,
	});

	toast.showToast();

	return toast;
};
