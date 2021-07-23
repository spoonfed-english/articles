(function()
{
	
	const POSRegex = /^([a-z]+)\t(.+)$/gm;
	const POSSub = `<span class="pos">$1</span> <span class="text">$2</span>`;
	
	const ValidWordLists = ['ielts', 'cet6', 'off'];
	const ValidThemes = ['light', 'dark'];
	const TippyThemes = {
		'light': 'light-border',
		'dark': 'dark',
	}
	const ThemeRegex = new RegExp(`\\s*(${Object.values(TippyThemes).join('|')})\\s*`, 'g');
	
	const $content = document.querySelector('section.text');
	const wordListButtons = {};
	const $nightModeButton = document.getElementById('night-mode-btn');
	
	let wordList = load('wordList', ValidWordLists[0], ValidWordLists);
	let theme = load('theme', ValidThemes[0], ValidThemes);
	
	function init()
	{
		if(ValidWordLists.indexOf(wordList) === -1)
		{
			wordList = ValidWordLists[0];
		}
		
		setPageClass();
		setContentClass();
		
		const $wordListButtons = document.querySelectorAll('.word-lists .item');
		for(const $button of $wordListButtons)
		{
			$button.addEventListener('click', onWordListButtonClick);
			$button.classList.remove('active');
			const type = $button.dataset.type;
			wordListButtons[type] = $button;
		}
		
		$nightModeButton.classList.toggle('active', theme === 'dark');
		$nightModeButton.addEventListener('click', onNightModeButtonClick);
		
		wordListButtons[wordList].classList.add('active');
		
		tippy.delegate('section.text', {
			target: 'span.word',
			touch: true,
			content: '...',
			trigger: 'click',
			// hideOnClick: false,
			interactive: true,
			allowHTML: true,
			onShow: onWordTooltipShow,
			theme: 'definition-popup',
		});
		tippy('[data-tippy-content]', {
			touch: true,
			allowHTML: true,
			onShow: onTooltipShow,
			theme: 'help-popup',
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
	
	function changeTheme(newTheme)
	{
		if(theme === newTheme)
			return;
		if(ValidThemes.indexOf(newTheme) === -1)
			return;
		
		$nightModeButton.classList.toggle('active', newTheme === 'dark');
		
		theme = newTheme;
		store('theme', theme);
		setPageClass();
	}
	
	function setPageClass()
	{
		for(const theme of ValidThemes)
		{
			document.body.classList.remove(`theme-${theme}`);
		}
		
		document.body.classList.add(`theme-${theme}`);
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
	
	function onNightModeButtonClick()
	{
		changeTheme($nightModeButton.classList.contains('active') ? 'light' : 'dark');
	}
	
	function onTooltipShow(instance)
	{
		const tippyTheme = TippyThemes[theme];
		
		const $tippyDiv = instance.popper.querySelector('.tippy-box');
		const tippyThemeClass = $tippyDiv.dataset.theme.replace(ThemeRegex, '');
		
		instance.setProps({
			theme: `${tippyTheme} ${tippyThemeClass}`,
		});
	}
	
	function onWordTooltipShow(instance)
	{
		onTooltipShow(instance);
		
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

function load(name, defaultValue, validValues)
{
	const value = localStorage.getItem(name) || defaultValue;
	
	if(validValues && validValues.length && validValues.indexOf(value) === -1)
		return validValues[0];
	
	return value;
}
