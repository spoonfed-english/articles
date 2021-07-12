(function()
{
	
	const POSRegex = /^([a-z]+)\t(.+)$/gm;
	const POSSub = `<span class="pos">$1</span> <span class="text">$2</span>`;
	
	function onTooltipShow(instance){
		const $word = instance.reference;
		const word = $word.innerText;
		const key = $word.dataset.lemma || word;
		let definition = DICT[key];
		
		if(!definition)
			return false;
		
		if(definition[0] !== '<')
		{
			definition = definition.replace(POSRegex, POSSub);
			
			if(definition[0] !== '<')
			{
				definition = `<span class="text">${definition}</span>`;
			}
		}
		
		instance.setContent(`<div class="definitions">${definition}</div>`);
	}
	
	tippy.delegate('section.text', {
		target: 'span.word',
		touch: true,
		content: '...',
		trigger: 'focus',
		interactive: true,
		allowHTML: true,
		theme: 'light-border definition-popup',
		onShow: onTooltipShow
	});
})();
