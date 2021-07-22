(function()
{
	
	const POSRegex = /^([a-z]+)\t(.+)$/gm;
	const POSSub = `<span class="pos">$1</span> <span class="text">$2</span>`;
	
	const ValidWordLists = ['ielts', 'cet6', 'off'];
	
	const $content = document.querySelector('section.text');
	const wordListButtons = {};
	
	let wordList = load('wordList', 'ielts');
	
	function init()
	{
		if(ValidWordLists.indexOf(wordList) === -1)
		{
			wordList = ValidWordLists[0];
		}
		
		setContentClass();
		
		const $wordListButtons = document.querySelectorAll('.word-lists .item');
		for(const $button of $wordListButtons)
		{
			$button.addEventListener('click', onWordListButtonClick);
			$button.classList.remove('active');
			const type = $button.dataset.type;
			wordListButtons[type] = $button;
		}
		
		wordListButtons[wordList].classList.add('active');
		
		tippy.delegate('section.text', {
			target: 'span.word',
			touch: true,
			content: '...',
			trigger: 'focus',
			interactive: true,
			allowHTML: true,
			theme: 'light-border definition-popup',
			onShow: onTooltipShow,
		});
		tippy('[data-tippy-content]', {
			touch: true,
			allowHTML: true,
			theme: 'light-border help-popup',
		});
	}
	
	function changeWordList(newWordList)
	{
		if(wordList === newWordList)
			return;
		if(ValidWordLists.indexOf(newWordList) === -1)
			return;
		
		wordListButtons[wordList].classList.remove('active');
		wordListButtons[newWordList].classList.add('active');
		
		wordList = newWordList;
		store('wordList', wordList);
		
		setContentClass();
	}
	
	function setContentClass()
	{
		$content.className = '';
		$content.classList.add('text');
		
		if(wordList !== 'off')
		{
			$content.classList.add(wordList);
		}
	}
	
	function onTooltipShow(instance){
		const $word = instance.reference;
		
		if(!$word.classList.contains(wordList) && !$word.classList.contains('extra'))
			return false;
		
		const word = $word.innerText;
		const key = $word.dataset.lemma || word;
		let definition = DICT[key];
		
		if(!definition)
			return false;
		
		if(definition[0] === '>')
		{
			definition = DICT[definition.substring(1)];
		}
		
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
	
	function onWordListButtonClick(event)
	{
		changeWordList(event.target.dataset.type);
	}
	
	init();
	
})();

function store(name, value)
{
	return localStorage.setItem(name, value);
}

function load(name, defaultValue)
{
	return localStorage.getItem(name) || defaultValue;
}
