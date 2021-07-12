(function()
{
	function onTooltipShow(instance){
		const $word = instance.reference;
		const word = $word.innerText;
		const key = $word.dataset.lemma || word;
		const definition = DICT[key];
		
		if(!definition)
			return false;
		
		instance.setContent(definition);
	}
	
	tippy.delegate('section.text', {
		target: 'span.word',
		touch: true,
		content: '...',
		trigger: 'click focus',
		interactive: true,
		theme: 'light-border definition-popup',
		onShow: onTooltipShow
	});
})();
